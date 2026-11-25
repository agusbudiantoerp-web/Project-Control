"""Unified project schedule and cost outlook using existing workspace engines."""
from __future__ import annotations

from datetime import date
from typing import Any

from .cost_forecast import build_cost_forecast
from .schedule_forecast import assess_schedule_delays


def build_schedule_cost_outlook(
    evm: dict[str, Any],
    activities: list[dict[str, Any]],
    *,
    as_of_date: str | date,
    warning_threshold_pct: float = 5.0,
) -> dict[str, Any]:
    """Combine EVM cost scenarios with explicit activity finish-date forecasts."""
    if not isinstance(evm, dict):
        raise TypeError("evm must be a dictionary")
    if not isinstance(activities, list):
        raise TypeError("activities must be a list")
    cost = build_cost_forecast(evm, warning_threshold_pct=warning_threshold_pct)
    schedule = assess_schedule_delays(activities, as_of_date=as_of_date)
    schedule_has_dates = bool(activities) and all(
        row.get("baseline_finish_date") not in (None, "")
        and row.get("forecast_finish_date") not in (None, "")
        for row in activities
    )
    if cost["status"] == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    elif cost["status"] == "ASSESSED" and schedule["status"] == "ASSESSED" and schedule_has_dates:
        status = "ASSESSED"
    elif cost["status"] == "INSUFFICIENT_DATA" and not schedule.get("activities"):
        status = "INSUFFICIENT_DATA"
    else:
        status = "PARTIALLY_ASSESSED"
    over_budget = [
        item["scenario"] for item in cost.get("scenarios", [])
        if item.get("status") == "OVER_BUDGET"
    ]
    return {
        "status": status,
        "project_id": evm.get("project_id"),
        "currency": evm.get("currency"),
        "cost_forecast": cost,
        "schedule_forecast": schedule,
        "management_attention": {
            "project_delay_days": schedule.get("project_delay_days"),
            "delayed_activity_ids": schedule.get("delayed_activity_ids", []),
            "unassessed_activity_ids": schedule.get("unassessed_activity_ids", []),
            "cost_scenarios_over_budget": over_budget,
        },
        "limitations": [
            "Cost and schedule use separately supplied evidence; no causal relationship is inferred.",
            "Project finish delay is assessed only when every activity has baseline and forecast finish dates.",
            "Schedule variance uses calendar days; working calendars, holidays and contract rules are not applied.",
            "Cost estimates exclude commitments, accruals, risk, escalation, tax and change orders unless already reflected in EVM inputs.",
            "This outlook is decision support, not an approved revised baseline or budget.",
        ],
    }
