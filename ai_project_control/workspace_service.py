"""Read-only workspace overview assembled from the local project store."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .data_quality_validation import TABLE_KEYS
from .portfolio_performance import build_portfolio_scorecard
from .project_store import ProjectStore
from .evm_engine import calculate_evm
from .schedule_engine import calculate_critical_path
from .schedule_forecast import assess_schedule_delays
from .schedule_baseline_service import compare_schedule_to_baseline


def build_workspace_overview(database_path: str | Path, project_id: str) -> dict[str, Any]:
    project_id = str(project_id).strip()
    if not project_id:
        raise ValueError("project_id is required")
    store = ProjectStore(database_path)
    workspace = store.load_project_workspace(project_id)
    master = workspace["project_master"]
    if not master:
        raise ValueError(f"Project '{project_id}' was not found in this workspace")

    project = master[0]
    scorecard = build_portfolio_scorecard([{
        "project_id": project_id,
        "project_name": project.get("project_name", ""),
        "SPI": project.get("SPI", project.get("spi")),
        "CPI": project.get("CPI", project.get("cpi")),
        "risk_score": project.get("risk_score"),
        "overloaded_resource_days": project.get("overloaded_resource_days"),
        "currency": project.get("currency", ""),
        "budget_at_completion": project.get("budget_at_completion", project.get("bac")),
    }])
    evm = calculate_evm(project, workspace["progress"], workspace["actual_cost"])
    schedule = calculate_critical_path(workspace["activities"])
    schedule_forecast = assess_schedule_delays(
        workspace["activities"],
        as_of_date=__import__("datetime").date.today(),
    )
    approved_baselines = [
        baseline for baseline in workspace.get("schedule_baselines", [])
        if str(baseline.get("status", "")).upper() == "APPROVED"
    ]
    approved_baselines.sort(
        key=lambda item: (
            int(item.get("version", 0) or 0),
            str(item.get("approved_at", "")),
            str(item.get("baseline_id", "")),
        )
    )
    active_baseline = approved_baselines[-1] if approved_baselines else None
    schedule_variance = (
        compare_schedule_to_baseline(active_baseline, workspace["activities"])
        if active_baseline else {
            "status": "NO_APPROVED_BASELINE",
            "baseline_activity_count": 0,
            "current_activity_count": len(workspace["activities"]),
            "added_activity_ids": [],
            "removed_activity_ids": [],
            "changed_activities": [],
            "added_count": 0,
            "removed_count": 0,
            "changed_count": 0,
        }
    )
    return {
        "project": project,
        "evm": evm,
        "schedule": schedule,
        "schedule_forecast": schedule_forecast,
        "active_schedule_baseline": active_baseline,
        "schedule_variance": schedule_variance,
        "dataset_counts": {name: len(workspace[name]) for name in TABLE_KEYS},
        "total_records": sum(len(rows) for rows in workspace.values()),
        "validation": store.validate_workspace(project_id),
        "scorecard": scorecard,
        "recent_imports": store.import_history(project_id, limit=20),
        "workspace": workspace,
        "limitations": [
            "Portfolio SPI/CPI indicators are assessed only when present in Project Master.",
            "Empty datasets mean no records are stored; they do not prove zero activity or zero risk.",
            "This overview reads a local SQLite file and does not provide multi-user synchronization.",
        ],
    }
