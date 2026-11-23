"""Cross-project command center assembled from the local SQLite project store."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .project_store import ProjectStore
from .evm_engine import calculate_evm
from .schedule_forecast import assess_schedule_delays
from .resource_loading_summary import build_resource_loading_summary
from .risk_cost_simulation import build_risk_cost_simulation
from .project_director_decision_matrix import build_decision_matrix
from .portfolio_performance import build_portfolio_scorecard


def build_portfolio_command_center(database_path: str | Path) -> dict[str, Any]:
    """Summarize every locally stored project without combining unlike currencies."""
    store = ProjectStore(database_path)
    with store._connect() as db:
        ids = [row["project_id"] for row in db.execute(
            "SELECT DISTINCT project_id FROM project_records WHERE dataset='project_master' ORDER BY project_id"
        ).fetchall()]

    records: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for project_id in ids:
        workspace = store.load_project_workspace(project_id)
        if not workspace["project_master"]:
            continue
        project = workspace["project_master"][0]
        evm = calculate_evm(project, workspace["progress"], workspace["actual_cost"])
        schedule = assess_schedule_delays(
            workspace["activities"],
            as_of_date=__import__("datetime").date.today(),
        )
        resources = build_resource_loading_summary(workspace["resources"])
        currency = str(project.get("currency", "")).strip().upper()
        base_cost = evm.get("BAC")
        risk_result = None
        if workspace["risk"] and base_cost is not None and currency:
            risk_result = build_risk_cost_simulation(
                workspace["risk"], base_cost, currency, iterations=5000, seed=42
            )
        record = {
            "project_id": project_id,
            "project_name": project.get("project_name", ""),
            "SPI": evm.get("SPI"),
            "CPI": evm.get("CPI"),
            "risk_score": project.get("risk_score"),
            "overloaded_resource_days": project.get("overloaded_resource_days"),
            "currency": currency,
            "budget_at_completion": base_cost,
        }
        records.append(record)
        details.append({
            "project_id": project_id,
            "project_name": project.get("project_name", ""),
            "SPI": evm.get("SPI"),
            "CPI": evm.get("CPI"),
            "EAC": evm.get("EAC"),
            "VAC": evm.get("VAC"),
            "currency": currency,
            "budget_at_completion": base_cost,
            "schedule_status": schedule.get("status"),
            "delayed_activity_count": len(schedule.get("delayed_activity_ids", [])),
            "unassessed_activity_count": len(schedule.get("unassessed_activity_ids", [])),
            "resource_status": resources.get("status"),
            "resource_overloaded_count": resources.get("overloaded_count", 0),
            "resource_unassessed_count": resources.get("unassessed_count", 0),
            "risk_status": risk_result.get("status") if risk_result else "UNASSESSED",
            "risk_p80_contingency": risk_result.get("p80_contingency") if risk_result else None,
            "risk_currency": risk_result.get("currency") if risk_result else currency,
        })

    scorecard = build_portfolio_scorecard(records)
    decisions = build_decision_matrix(records)
    detail_by_id = {row["project_id"]: row for row in details}
    ranked = []
    for decision in decisions["decisions"]:
        ranked.append({**decision, **detail_by_id.get(decision["project_id"], {})})
    return {
        "status": "NO_PROJECTS" if not ids else "ASSESSED",
        "project_count": len(ids),
        "projects": ranked,
        "performance_scorecard": scorecard,
        "decision_summary": decisions["summary"],
        "budget_by_currency": scorecard["summary"]["budget_by_currency"],
        "limitations": [
            "Only projects stored in this local SQLite database are included.",
            "P1/P2 is a screening heuristic using supplied SPI, CPI, risk_score and overloaded_resource_days; it is not a project approval.",
            "Schedule and resource counts are separate evidence and are not silently converted into risk scores or overload days.",
            "Risk P80 contingency is calculated only where a risk register, BAC and currency are available.",
            "Budget totals remain separated by currency; no foreign-exchange conversion is assumed.",
            "This local SQLite workspace is not a synchronized multi-user portfolio database.",
        ],
    }
