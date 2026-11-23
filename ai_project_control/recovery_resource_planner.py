"""Resource-based recovery screening using explicit productivity and cost assumptions.

This is a work-package capacity calculator, not a CPM network simulation.
"""
from __future__ import annotations

import math
from typing import Any


def _positive(value: Any, field: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(number) or (number < 0 if allow_zero else number <= 0):
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise ValueError(f"{field} must be finite and {qualifier}")
    return number


def estimate_resource_recovery(
    *,
    remaining_work_units: Any,
    current_daily_productivity: Any,
    additional_crew_count: Any = 0,
    productivity_per_additional_crew: Any = 0,
    additional_equipment_count: Any = 0,
    productivity_per_additional_equipment: Any = 0,
    efficiency_factor: Any = 1.0,
    current_daily_cost: Any = 0,
    additional_crew_daily_cost: Any = 0,
    additional_equipment_daily_cost: Any = 0,
    working_days_per_week: Any = 5,
    currency: str = "IDR",
) -> dict[str, Any]:
    """Estimate remaining work duration and incremental resource cost.

    Productivity inputs are work units per working day. Cost inputs use the
    same currency per working day. Added resource costs are charged for the
    estimated accelerated duration; no overtime premiums or mobilization costs
    are inferred.
    """
    work = _positive(remaining_work_units, "remaining_work_units")
    base_rate = _positive(current_daily_productivity, "current_daily_productivity")
    crews = _positive(additional_crew_count, "additional_crew_count", allow_zero=True)
    crew_rate = _positive(productivity_per_additional_crew, "productivity_per_additional_crew", allow_zero=True)
    equipment = _positive(additional_equipment_count, "additional_equipment_count", allow_zero=True)
    equipment_rate = _positive(productivity_per_additional_equipment, "productivity_per_additional_equipment", allow_zero=True)
    efficiency = _positive(efficiency_factor, "efficiency_factor")
    if efficiency > 1:
        raise ValueError("efficiency_factor must be between 0 and 1")
    if crews and crew_rate <= 0:
        raise ValueError("productivity_per_additional_crew must be positive when crews are added")
    if equipment and equipment_rate <= 0:
        raise ValueError("productivity_per_additional_equipment must be positive when equipment is added")
    base_cost = _positive(current_daily_cost, "current_daily_cost", allow_zero=True)
    crew_cost = _positive(additional_crew_daily_cost, "additional_crew_daily_cost", allow_zero=True)
    equipment_cost = _positive(additional_equipment_daily_cost, "additional_equipment_daily_cost", allow_zero=True)
    days_week = _positive(working_days_per_week, "working_days_per_week")
    if days_week > 7:
        raise ValueError("working_days_per_week cannot exceed 7")

    effective_added_rate = (crews * crew_rate + equipment * equipment_rate) * efficiency
    accelerated_rate = base_rate + effective_added_rate
    baseline_days = work / base_rate
    accelerated_days = work / accelerated_rate
    days_saved = max(0.0, baseline_days - accelerated_days)
    incremental_daily_cost = crews * crew_cost + equipment * equipment_cost
    baseline_cost = baseline_days * base_cost
    accelerated_total_cost = accelerated_days * (base_cost + incremental_daily_cost)
    incremental_cost = accelerated_total_cost - baseline_cost

    return {
        "status": "ASSESSED",
        "currency": str(currency or "").strip().upper() or None,
        "remaining_work_units": work,
        "baseline": {
            "daily_productivity": base_rate,
            "duration_working_days": round(baseline_days, 2),
            "estimated_remaining_cost": round(baseline_cost, 2),
        },
        "recovery": {
            "additional_crew_count": int(crews) if crews.is_integer() else crews,
            "additional_equipment_count": int(equipment) if equipment.is_integer() else equipment,
            "efficiency_factor": efficiency,
            "daily_productivity": round(accelerated_rate, 4),
            "duration_working_days": round(accelerated_days, 2),
            "days_saved": round(days_saved, 2),
            "incremental_daily_cost": round(incremental_daily_cost, 2),
            "estimated_total_cost": round(accelerated_total_cost, 2),
            "incremental_cost_vs_baseline": round(incremental_cost, 2),
        },
        "calendar_equivalent": {
            "working_days_per_week": int(days_week) if days_week.is_integer() else days_week,
            "baseline_weeks": round(baseline_days / days_week, 2),
            "recovery_weeks": round(accelerated_days / days_week, 2),
        },
        "assumptions": [
            "Productivity is additive and constant; actual crew/equipment interaction may be non-linear.",
            "Efficiency factor applies only to added-resource productivity.",
            "Costs are per working day in one consistent currency; mobilization, overtime, standby and indirect costs are excluded unless included in inputs.",
            "This is a work-package estimate, not a CPM network or critical-path recalculation.",
            "Safety, workface congestion, permits, quality, material availability and resource availability require independent validation.",
        ],
    }
