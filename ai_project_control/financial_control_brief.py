"""Integrated EVM and cost forecast decision brief."""
from __future__ import annotations

from typing import Any

from ai_project_control.evm_engine import calculate_evm
from ai_project_control.cost_forecast import build_cost_forecast


def build_financial_control_brief(
    project: dict[str, Any],
    progress_rows: list[dict[str, Any]],
    actual_cost_rows: list[dict[str, Any]],
    *,
    as_of_period: str | None = None,
    warning_threshold_pct: float = 5.0,
    progress_record_mode: str = "period_delta",
    actual_cost_record_mode: str = "period_delta",
) -> dict[str, Any]:
    """Connect source-record EVM calculation to transparent EAC scenarios."""
    evm = calculate_evm(
        project, progress_rows, actual_cost_rows, as_of_period=as_of_period,
        progress_record_mode=progress_record_mode,
        actual_cost_record_mode=actual_cost_record_mode,
    )
    forecast = build_cost_forecast(evm, warning_threshold_pct=warning_threshold_pct)
    alerts = []
    if evm.get("SPI") is not None and evm["SPI"] < 1:
        alerts.append({"code": "SCHEDULE_PERFORMANCE_BELOW_PLAN", "severity": "HIGH",
                       "message": "SPI is below 1. Review schedule drivers and critical activities."})
    if evm.get("CPI") is not None and evm["CPI"] < 1:
        alerts.append({"code": "COST_PERFORMANCE_BELOW_PLAN", "severity": "HIGH",
                       "message": "CPI is below 1. Review cost productivity and remaining-work assumptions."})
    if forecast.get("status") != "ASSESSED":
        alerts.append({"code": "COST_FORECAST_UNASSESSED", "severity": "DATA_GAP",
                       "message": "Cost forecast scenarios cannot be assessed from the available EVM inputs."})
    for scenario in forecast.get("scenarios", []):
        if scenario.get("status") == "OVER_BUDGET":
            alerts.append({"code": "EAC_SCENARIO_OVER_BUDGET", "severity": "HIGH",
                           "scenario": scenario["scenario"],
                           "variance_pct": scenario["variance_pct"]})
    return {
        "project_id": evm["project_id"],
        "as_of_period": as_of_period,
        "currency": evm.get("currency", ""),
        "status": "ASSESSED" if evm["status"] == "ASSESSED" and forecast["status"] == "ASSESSED" else "REVIEW_REQUIRED",
        "evm": evm,
        "cost_forecast": forecast,
        "management_alerts": alerts,
        "decision_guardrails": [
            "EAC scenarios are estimates, not approved budget revisions.",
            "Confirm the source valuation basis, period convention and currency before management use.",
            "Do not add forecast cash transactions to actual cost or treat EAC as a cash-flow schedule.",
        ],
    }
