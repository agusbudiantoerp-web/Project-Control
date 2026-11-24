"""Build a portfolio scorecard plus risk governance from persisted local records."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_project_control.action_register_store import ActionRegisterStore
from ai_project_control.evm_engine import calculate_evm
from ai_project_control.portfolio_executive_report import build_portfolio_executive_report
from ai_project_control.portfolio_performance import build_portfolio_scorecard
from ai_project_control.portfolio_health_monitoring import build_health_monitoring
from ai_project_control.project_store import ProjectStore
from ai_project_control.risk_exposure_matrix import build_risk_exposure_matrix
from ai_project_control.risk_governance_bridge import build_risk_governance_view
from ai_project_control.risk_mitigation_store import RiskMitigationStore
from ai_project_control.portfolio_workspace_intelligence import build_stored_portfolio_risk_resource_view
from ai_project_control.schedule_cost_outlook import build_schedule_cost_outlook
from ai_project_control.resource_loading_summary import build_resource_loading_summary
from ai_project_control.portfolio_cashflow_intelligence import build_portfolio_cashflow_view
from ai_project_control.project_director_decision_matrix import build_decision_matrix
from ai_project_control.coo_portfolio_decision_brief import build_coo_portfolio_decision_brief


def build_saved_portfolio_report(
    database_path: str | Path,
    *,
    as_of_period: str | None = None,
    language: str = "id",
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Discover saved projects and calculate EVM, risk exposure and governance."""
    store = ProjectStore(database_path)
    action_store = ActionRegisterStore(database_path)
    mitigation_store = RiskMitigationStore(database_path)
    records: list[dict[str, Any]] = []
    project_results: list[dict[str, Any]] = []
    governance_results: list[dict[str, Any]] = []
    risk_matrix_results: list[dict[str, Any]] = []
    health_snapshots: list[dict[str, Any]] = []
    schedule_cost_outlooks: list[dict[str, Any]] = []
    resource_loading_results: list[dict[str, Any]] = []
    project_finance_records: list[dict[str, Any]] = []
    decision_records: list[dict[str, Any]] = []
    for project_id in store.list_project_ids():
        workspace = store.load_project_workspace(project_id)
        if not workspace["project_master"]:
            continue
        project = workspace["project_master"][0]
        name = str(project.get("project_name") or project_id)
        currency = str(project.get("currency") or "").strip().upper()
        try:
            for dataset in ("progress", "actual_cost"):
                mismatch = sorted({
                    str(row.get("currency", "")).strip().upper()
                    for row in workspace[dataset]
                    if str(row.get("currency", "")).strip() and currency
                    and str(row.get("currency", "")).strip().upper() != currency
                })
                if mismatch:
                    raise ValueError(f"{dataset} currency mismatch: {', '.join(mismatch)}")
            evm = calculate_evm(
                project, workspace["progress"], workspace["actual_cost"],
                as_of_period=as_of_period,
            )
            records.append({
                "project_id": project_id, "project_name": name,
                "SPI": evm.get("SPI"), "CPI": evm.get("CPI"),
                "currency": currency, "budget_at_completion": project.get("BAC"),
            })
            if as_of_date:
                outlook = build_schedule_cost_outlook(
                    {**evm, "project_id": project_id, "currency": currency},
                    workspace["activities"], as_of_date=as_of_date,
                )
            else:
                outlook = {
                    "status": "NOT_RUN", "project_id": project_id, "currency": currency,
                    "reason": "Provide as_of_date (YYYY-MM-DD) for dated schedule outlook.",
                }
            schedule_cost_outlooks.append({"project_id": project_id, "project_name": name, **outlook})
            project_results.append({
                "project_id": project_id, "project_name": name,
                "status": evm.get("status"), "currency": currency,
                "evm": evm, "source_counts": {
                    "progress": len(workspace["progress"]),
                    "actual_cost": len(workspace["actual_cost"]),
                    "risk": len(workspace["risk"]),
                    "activities": len(workspace["activities"]),
                    "wbs": len(workspace["wbs"]),
                },
                "validation": store.validate_workspace(project_id),
            })
        except (TypeError, ValueError, KeyError) as exc:
            schedule_cost_outlooks.append({
                "project_id": project_id, "project_name": name,
                "status": "REVIEW_REQUIRED", "currency": currency,
                "reason": f"Cost/schedule outlook could not be assessed: {exc}",
            })
            records.append({
                "project_id": project_id, "project_name": name,
                "SPI": None, "CPI": None, "currency": currency,
                "budget_at_completion": project.get("BAC"),
            })
            project_results.append({
                "project_id": project_id, "project_name": name,
                "status": "REVIEW_REQUIRED", "currency": currency,
                "error": str(exc),
            })

        health_snapshots.extend(workspace["portfolio_snapshots"])
        try:
            actual_cost_total = (
                sum(float(row["actual_cost"]) for row in workspace["actual_cost"])
                if workspace["actual_cost"] else None
            )
        except (TypeError, ValueError, KeyError):
            actual_cost_total = None
        budget_value = project.get("BAC")
        if budget_value in (None, "") and workspace["boq"]:
            try:
                budget_value = sum(float(row["amount"]) for row in workspace["boq"] if row.get("amount") not in (None, ""))
            except (TypeError, ValueError, KeyError):
                budget_value = None
        project_finance_records.append({
            "project_id": project_id, "project_name": name,
            "currency": currency, "budget": budget_value,
            "actual_cost": actual_cost_total,
        })
        resource_loading = build_resource_loading_summary(workspace["resources"])
        resource_loading_results.append({
            "project_id": project_id, "project_name": name,
            "status": resource_loading["status"],
            "overloaded_count": resource_loading["overloaded_count"],
            "unassessed_count": resource_loading["unassessed_count"],
            "rows": resource_loading["rows"].to_dict(orient="records"),
        })
        risks = workspace["risk"]
        valid_risk_scores = []
        for risk_row in risks:
            try:
                value = float(risk_row.get("risk_score"))
                if value == value and abs(value) != float("inf"):
                    valid_risk_scores.append(value)
            except (TypeError, ValueError):
                pass
        delayed_count = 0
        if schedule_cost_outlooks and schedule_cost_outlooks[-1].get("project_id") == project_id:
            delayed_count = len(
                (schedule_cost_outlooks[-1].get("schedule_forecast") or {}).get("delayed_activity_ids", [])
            )
        decision_records.append({
            "project_id": project_id, "project_name": name,
            "SPI": evm.get("SPI") if "evm" in locals() and isinstance(evm, dict) else None,
            "CPI": evm.get("CPI") if "evm" in locals() and isinstance(evm, dict) else None,
            "risk_score": max(valid_risk_scores) if valid_risk_scores else None,
            "overloaded_resource_days": resource_loading["overloaded_count"],
            "forecast_variance_days": None,
            "schedule_status": "DELAYED" if delayed_count else "UNASSESSED",
            "delayed_activity_count": delayed_count,
            "resource_overloaded_count": resource_loading["overloaded_count"],
            "risk_status": "ASSESSED" if valid_risk_scores else ("NO_RISKS" if not risks else "INVALID_DATA"),
            "currency": currency,
        })
        actions = action_store.list_project(project_id)["actions"]
        mitigations = mitigation_store.list_project(project_id)
        governance = build_risk_governance_view(
            risks, actions, mitigations, as_of_date=as_of_date
        )
        matrix = build_risk_exposure_matrix(
            risks, activities=workspace["activities"], wbs=workspace["wbs"]
        )
        governance_results.append({
            "project_id": project_id, "project_name": name, **governance,
        })
        risk_matrix_results.append({
            "project_id": project_id, "project_name": name, **matrix,
        })

    scorecard = build_portfolio_scorecard(records)
    health_monitoring = build_health_monitoring(health_snapshots)
    portfolio_cashflow = build_portfolio_cashflow_view(project_finance_records)
    portfolio_resource_intelligence = build_stored_portfolio_risk_resource_view(database_path)
    decision_matrix = build_decision_matrix(decision_records)
    decision_rows = []
    for source, scored in zip(decision_records, decision_matrix["decisions"]):
        decision_rows.append({**source, **scored})
    decision_matrix["decisions"] = decision_rows
    decision_portfolio = {"project_count": len(decision_rows), "projects": decision_rows}
    coo_decision_brief = build_coo_portfolio_decision_brief(
        decision_portfolio, portfolio_resource_intelligence,
        action_store.list_portfolio(), as_of_date=as_of_date,
    )
    report = build_portfolio_executive_report(records, as_of_period or "Latest saved data", language)
    governance_summary = {
        "project_count": len(governance_results),
        "risk_count": sum(row["risk_count"] for row in governance_results),
        "risks_requiring_attention": sum(row["risks_requiring_attention"] for row in governance_results),
        "overdue_action_count": sum(row["overdue_action_count"] for row in governance_results),
        "blocked_action_count": sum(row["blocked_action_count"] for row in governance_results),
        "risks_without_mitigation": sum(row["risks_without_mitigation"] for row in governance_results),
        "orphan_action_count": sum(row["orphan_action_count"] for row in governance_results),
    }
    report += "\n## COO decision brief\n"
    report += f"- Projects requiring management review: {coo_decision_brief['projects_requiring_review']}\n"
    report += f"- Executive actions overdue: {coo_decision_brief['executive_action_summary'].get('overdue_count', 0)}\n"
    report += f"- Executive actions blocked: {coo_decision_brief['executive_action_summary'].get('blocked_count', 0)}\n"
    for recommendation in coo_decision_brief["recommended_management_reviews"]:
        report += f"- Management review: {recommendation}\n"
    report += "\n## Risk governance\n"
    report += f"- Projects with governance review: {governance_summary['project_count']}\n"
    report += f"- Registered risks: {governance_summary['risk_count']}\n"
    report += f"- Risks requiring attention: {governance_summary['risks_requiring_attention']}\n"
    report += f"- Overdue linked actions: {governance_summary['overdue_action_count']}\n"
    report += f"- Blocked linked actions: {governance_summary['blocked_action_count']}\n"
    report += f"- Risks without mitigation plan: {governance_summary['risks_without_mitigation']}\n"
    report += "- Risk attention flags are governance worklist signals, not an automated risk acceptance decision.\n"
    report += "\n## Portfolio health trends\n"
    report += f"- Projects with dated health snapshots: {health_monitoring['summary']['project_count']}\n"
    report += f"- Trends assessed: {health_monitoring['summary']['trend_assessed_count']}\n"
    report += f"- Projects without baseline: {health_monitoring['summary']['no_baseline_count']}\n"
    report += f"- Snapshot conflicts: {health_monitoring['summary']['data_conflict_count']}\n"
    report += "\n## Resource loading\n"
    report += f"- Projects with resource overload: {sum(item['overloaded_count'] > 0 for item in resource_loading_results)}\n"
    report += f"- Resource periods overloaded: {sum(item['overloaded_count'] for item in resource_loading_results)}\n"
    report += f"- Resource periods unassessed: {sum(item['unassessed_count'] for item in resource_loading_results)}\n"
    report += "\n## Portfolio financial position (currency-separated)\n"
    report += f"- Projects with assessed finance: {portfolio_cashflow['project_count_assessed']}\n"
    report += f"- Projects with incomplete finance data: {portfolio_cashflow['project_count_unassessed']}\n"
    report += f"- Projects above supplied budget: {portfolio_cashflow['projects_over_budget']}\n"
    for currency_code, totals in portfolio_cashflow["totals_by_currency"].items():
        report += f"- {currency_code}: budget={totals['budget']:,.2f}; actual cost={totals['actual_cost']:,.2f}; remaining={totals['remaining_budget']:,.2f}\n"
    report += "\n## Schedule and cost outlook\n"
    report += f"- Projects with outlook: {sum(item.get('status') in ('ASSESSED', 'PARTIALLY_ASSESSED') for item in schedule_cost_outlooks)}\n"
    report += f"- Projects requiring an as-of date: {sum(item.get('status') == 'NOT_RUN' for item in schedule_cost_outlooks)}\n"
    for item in schedule_cost_outlooks:
        attention = item.get("management_attention", {})
        if attention.get("delayed_activity_ids") or attention.get("cost_scenarios_over_budget"):
            report += f"- {item['project_name']}: delayed activities={', '.join(attention.get('delayed_activity_ids', [])) or 'none'}; over-budget scenarios={', '.join(attention.get('cost_scenarios_over_budget', [])) or 'none'}\n"
    return {
        "project_count": len(project_results),
        "scorecard": scorecard,
        "projects": project_results,
        "risk_governance": governance_results,
        "risk_governance_summary": governance_summary,
        "risk_exposure_matrices": risk_matrix_results,
        "health_monitoring": health_monitoring,
        "portfolio_resource_intelligence": portfolio_resource_intelligence,
        "schedule_cost_outlooks": schedule_cost_outlooks,
        "resource_loading": resource_loading_results,
        "portfolio_cashflow": portfolio_cashflow,
        "decision_matrix": decision_matrix,
        "coo_decision_brief": coo_decision_brief,
        "executive_report": report,
        "as_of_period": as_of_period,
        "as_of_date": as_of_date,
        "limitations": [
            "Only projects saved in this local SQLite workspace are included.",
            "Health trends use only explicitly captured dated snapshots; no historical values are reconstructed.",
            "Shared-resource conflicts require identical resource IDs, periods, units and capacity declarations across projects.",
            "Schedule/cost outlook requires an explicit as_of_date and dated activity forecast fields; missing evidence remains unassessed.",
            "Monetary risk exposure is meaningful only when risk impact values are actual monetary amounts in the project currency.",
            "SPI and CPI are calculated from saved period records; missing core values remain unassessed.",
            "Portfolio budget totals remain separated by currency; no FX conversion is performed.",
            "Period rows must be deltas, not cumulative snapshots, unless normalized before import.",
            "Risk exposure impact values must share one unit and currency within each project for ranking.",
            "Mitigation and action actor labels are attribution only, not authenticated identities.",
            "This local database is not shared between users or devices.",
        ],
    }
