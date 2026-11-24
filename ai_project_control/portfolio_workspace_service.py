"""Build a portfolio scorecard from all projects persisted in the local workspace."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_project_control.evm_engine import calculate_evm
from ai_project_control.portfolio_executive_report import build_portfolio_executive_report
from ai_project_control.portfolio_performance import build_portfolio_scorecard
from ai_project_control.project_store import ProjectStore


def build_saved_portfolio_report(
    database_path: str | Path,
    *,
    as_of_period: str | None = None,
    language: str = "id",
) -> dict[str, Any]:
    """Discover saved projects and calculate EVM-derived portfolio indicators."""
    store = ProjectStore(database_path)
    records: list[dict[str, Any]] = []
    project_results: list[dict[str, Any]] = []
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
            record = {
                "project_id": project_id, "project_name": name,
                "SPI": evm.get("SPI"), "CPI": evm.get("CPI"),
                "currency": currency,
                "budget_at_completion": project.get("BAC"),
            }
            records.append(record)
            project_results.append({
                "project_id": project_id, "project_name": name,
                "status": evm.get("status"), "currency": currency,
                "evm": evm, "source_counts": {
                    "progress": len(workspace["progress"]),
                    "actual_cost": len(workspace["actual_cost"]),
                },
                "validation": store.validate_workspace(project_id),
            })
        except (TypeError, ValueError, KeyError) as exc:
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
    scorecard = build_portfolio_scorecard(records)
    report = build_portfolio_executive_report(records, as_of_period or "Latest saved data", language)
    return {
        "project_count": len(project_results),
        "scorecard": scorecard,
        "projects": project_results,
        "executive_report": report,
        "as_of_period": as_of_period,
        "limitations": [
            "Only projects saved in this local SQLite workspace are included.",
            "SPI and CPI are calculated from saved period records; missing core values remain unassessed.",
            "Portfolio budget totals remain separated by currency; no FX conversion is performed.",
            "Period rows must be deltas, not cumulative snapshots, unless normalized before import.",
            "This local database is not shared between users or devices.",
        ],
    }
