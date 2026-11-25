"""Read persisted project records into an integrated financial-control brief."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_project_control.cost_forecast import build_cost_forecast
from ai_project_control.evm_engine import calculate_evm
from ai_project_control.project_store import ProjectStore


def build_stored_project_financial_control(
    database_path: str | Path,
    project_id: str,
    *,
    as_of_period: str | None = None,
    warning_threshold_pct: float = 5.0,
    progress_mode: str = "period_deltas",
) -> dict[str, Any]:
    """Calculate EVM and cost scenarios from one project's persisted workspace."""
    project_id = str(project_id).strip()
    if not project_id:
        raise ValueError("project_id is required")
    store = ProjectStore(database_path)
    workspace = store.load_project_workspace(project_id)
    if not workspace["project_master"]:
        raise ValueError(f"Project '{project_id}' was not found in the local workspace")
    project = workspace["project_master"][0]

    project_currency = str(project.get("currency", "")).strip().upper()
    for dataset in ("actual_cost", "progress"):
        mismatches = sorted({
            str(row.get("currency", "")).strip().upper()
            for row in workspace[dataset]
            if str(row.get("currency", "")).strip()
            and project_currency
            and str(row.get("currency", "")).strip().upper() != project_currency
        })
        if mismatches:
            raise ValueError(
                f"{dataset} contains currency values inconsistent with project currency "
                f"{project_currency}: {', '.join(mismatches)}"
            )

    evm = calculate_evm(
        project, workspace["progress"], workspace["actual_cost"],
        as_of_period=as_of_period,
        progress_mode=progress_mode,
    )
    forecast = build_cost_forecast(evm, warning_threshold_pct=warning_threshold_pct)
    alerts = []
    if evm.get("SPI") is not None and evm["SPI"] < 1:
        alerts.append({"code": "SCHEDULE_PERFORMANCE_BELOW_PLAN", "severity": "HIGH"})
    if evm.get("CPI") is not None and evm["CPI"] < 1:
        alerts.append({"code": "COST_PERFORMANCE_BELOW_PLAN", "severity": "HIGH"})
    if forecast["status"] != "ASSESSED":
        alerts.append({"code": "COST_FORECAST_NOT_ASSESSED", "severity": "DATA_GAP"})

    return {
        "project_id": project_id,
        "project_name": project.get("project_name", project_id),
        "currency": project_currency,
        "as_of_period": as_of_period,
        "progress_mode": progress_mode,
        "evm": evm,
        "cost_forecast": forecast,
        "management_alerts": alerts,
        "source_counts": {
            "progress": len(workspace["progress"]),
            "actual_cost": len(workspace["actual_cost"]),
        },
        "data_validation": store.validate_workspace(project_id),
        "limitations": [
            "This report reads records already saved in the local SQLite workspace; it does not import or modify data.",
            "The EVM engine supports period-delta aggregation or selecting the latest cumulative progress snapshot per activity. Actual-cost rows remain transaction/period deltas in both modes.",
            "Rows without a currency field inherit the project-level currency assumption; rows with an explicit different currency are rejected.",
            "EAC scenarios are estimates, not approved budget changes, cash commitments or a dated cash forecast.",
            "SQLite is local to this machine and is not a multi-user synchronized database.",
        ],
    }
