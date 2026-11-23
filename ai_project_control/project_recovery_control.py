"""Project recovery control calculations using explicit dates and supplied estimates.

The module never fabricates a recovery duration, cost, or target. It is a screening
calculator; approval and feasibility remain subject to project controls review.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any


def _as_date(value: Any, field: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a valid ISO date (YYYY-MM-DD)") from None


def _number(value: Any, field: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def assess_recovery_control(
    *,
    baseline_finish: Any,
    current_forecast_finish: Any,
    recovery_target_finish: Any = None,
    current_spi: Any = None,
    target_spi: Any = None,
    approved_recovery_budget: Any = None,
    estimated_recovery_cost: Any = None,
) -> dict[str, Any]:
    """Assess schedule recovery gap, SPI gap, and recovery funding gap."""
    baseline = _as_date(baseline_finish, "baseline_finish")
    forecast = _as_date(current_forecast_finish, "current_forecast_finish")
    target_finish = _as_date(recovery_target_finish, "recovery_target_finish")
    spi = _number(current_spi, "current_spi")
    spi_target = _number(target_spi, "target_spi")
    budget = _number(approved_recovery_budget, "approved_recovery_budget")
    cost = _number(estimated_recovery_cost, "estimated_recovery_cost")

    if spi is not None and spi < 0:
        raise ValueError("current_spi cannot be negative")
    if spi_target is not None and spi_target < 0:
        raise ValueError("target_spi cannot be negative")
    if budget is not None and budget < 0:
        raise ValueError("approved_recovery_budget cannot be negative")
    if cost is not None and cost < 0:
        raise ValueError("estimated_recovery_cost cannot be negative")

    baseline_variance_days = (forecast - baseline).days if baseline and forecast else None
    target_gap_days = (forecast - target_finish).days if forecast and target_finish else None
    spi_gap = round(spi_target - spi, 4) if spi is not None and spi_target is not None else None
    funding_gap = round(cost - budget, 2) if cost is not None and budget is not None else None

    missing = []
    if baseline is None:
        missing.append("baseline_finish")
    if forecast is None:
        missing.append("current_forecast_finish")
    if target_finish is None:
        missing.append("recovery_target_finish")
    if spi is None:
        missing.append("current_spi")
    if spi_target is None:
        missing.append("target_spi")
    if budget is None:
        missing.append("approved_recovery_budget")
    if cost is None:
        missing.append("estimated_recovery_cost")

    signals = []
    if baseline_variance_days is not None:
        if baseline_variance_days > 0:
            signals.append(f"Current forecast is {baseline_variance_days} days later than baseline.")
        elif baseline_variance_days < 0:
            signals.append(f"Current forecast is {abs(baseline_variance_days)} days earlier than baseline.")
        else:
            signals.append("Current forecast matches the baseline finish date.")
    if target_gap_days is not None:
        if target_gap_days > 0:
            signals.append(f"Recovery target is not met by {target_gap_days} days at the current forecast.")
        else:
            signals.append("Current forecast meets or beats the supplied recovery target.")
    if spi_gap is not None:
        signals.append(
            f"SPI is {abs(spi_gap):.3f} below target." if spi_gap > 0
            else ("SPI is above target." if spi_gap < 0 else "SPI matches target.")
        )
    if funding_gap is not None:
        signals.append(
            f"Estimated recovery cost exceeds approved budget by {funding_gap:,.2f}."
            if funding_gap > 0 else "Estimated recovery cost is within the supplied approved budget."
        )

    if missing:
        status = "INCOMPLETE_INPUT"
    elif (target_gap_days or 0) > 0 or (spi_gap or 0) > 0 or (funding_gap or 0) > 0:
        status = "RECOVERY_GAP"
    else:
        status = "TARGETS_MET"

    return {
        "status": status,
        "baseline_finish": baseline.isoformat() if baseline else None,
        "current_forecast_finish": forecast.isoformat() if forecast else None,
        "recovery_target_finish": target_finish.isoformat() if target_finish else None,
        "baseline_variance_days": baseline_variance_days,
        "recovery_target_gap_days": target_gap_days,
        "current_spi": spi,
        "target_spi": spi_target,
        "spi_gap": spi_gap,
        "approved_recovery_budget": budget,
        "estimated_recovery_cost": cost,
        "funding_gap": funding_gap,
        "missing_inputs": missing,
        "signals": signals or ["Supply validated project dates and recovery estimates to assess progress."],
        "limitations": [
            "Date variance is a finish-date comparison, not a CPM critical-path recalculation.",
            "SPI targets and cost estimates must be supplied from approved project-control records.",
            "This assessment does not authorize overtime, acceleration, budget changes or contract variations.",
        ],
    }
