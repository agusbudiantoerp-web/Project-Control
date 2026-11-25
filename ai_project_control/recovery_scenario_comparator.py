"""Compare explicitly supplied project recovery scenarios.

All scenario costs, durations and risk values must be supplied by the user. The
calculator ranks options by schedule benefit and cost efficiency; it does not
forecast feasibility or approve a recovery plan.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def _finite(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def compare_recovery_scenarios(
    scenarios: Iterable[dict[str, Any]],
    *,
    current_forecast_duration_days: Any,
    target_duration_days: Any = None,
) -> dict[str, Any]:
    """Rank scenarios with positive duration savings and explicit costs."""
    current = _finite(current_forecast_duration_days, "current_forecast_duration_days")
    if current <= 0:
        raise ValueError("current_forecast_duration_days must be greater than zero")
    target = None if target_duration_days in (None, "") else _finite(target_duration_days, "target_duration_days")
    if target is not None and target <= 0:
        raise ValueError("target_duration_days must be greater than zero")

    rows = []
    seen = set()
    for raw in scenarios:
        scenario_id = str(raw.get("scenario_id", "")).strip()
        name = str(raw.get("name", "")).strip()
        if not scenario_id or not name:
            raise ValueError("each scenario requires scenario_id and name")
        if scenario_id in seen:
            raise ValueError("scenario_id values must be unique")
        seen.add(scenario_id)
        saving = _finite(raw.get("duration_saving_days"), "duration_saving_days")
        cost = _finite(raw.get("incremental_cost"), "incremental_cost")
        risk = _finite(raw.get("risk_score"), "risk_score")
        if saving < 0 or saving > current:
            raise ValueError("duration_saving_days must be between zero and current duration")
        if cost < 0:
            raise ValueError("incremental_cost cannot be negative")
        if risk < 0 or risk > 100:
            raise ValueError("risk_score must be between 0 and 100")
        remaining = current - saving
        cost_per_day = cost / saving if saving > 0 else None
        target_gap = remaining - target if target is not None else None
        rows.append({
            "scenario_id": scenario_id,
            "name": name,
            "duration_saving_days": round(saving, 2),
            "remaining_duration_days": round(remaining, 2),
            "incremental_cost": round(cost, 2),
            "risk_score": round(risk, 2),
            "cost_per_day_saved": round(cost_per_day, 2) if cost_per_day is not None else None,
            "target_duration_gap_days": round(target_gap, 2) if target_gap is not None else None,
            "target_met": remaining <= target if target is not None else None,
            "assessment": (
                "NO_SCHEDULE_BENEFIT" if saving == 0 else
                "TARGET_NOT_MET" if target_gap is not None and target_gap > 0 else
                "TARGET_MET" if target_gap is not None else
                "BENEFIT_REQUIRES_REVIEW"
            ),
        })

    rows.sort(key=lambda row: (
        row["duration_saving_days"] <= 0,
        row["cost_per_day_saved"] if row["cost_per_day_saved"] is not None else math.inf,
        row["risk_score"],
        row["scenario_id"],
    ))
    return {
        "scenarios": rows,
        "summary": {
            "scenario_count": len(rows),
            "target_met_count": sum(row["target_met"] is True for row in rows),
            "no_schedule_benefit_count": sum(row["assessment"] == "NO_SCHEDULE_BENEFIT" for row in rows),
        },
        "method": (
            "Cost efficiency is incremental cost divided by supplied days saved. "
            "Options are ordered by cost per day saved, then risk score. This is a "
            "screening comparison; resource availability, CPM logic, safety, quality, "
            "contract constraints and probability of success require separate review."
        ),
    }
