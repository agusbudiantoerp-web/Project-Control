"""Transparent project cost forecast scenarios using Earned Value inputs."""
from __future__ import annotations

import math
from typing import Any


def _finite_nonnegative(value: Any, field: str) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def build_cost_forecast(evm: dict[str, Any], *, warning_threshold_pct: float = 5.0) -> dict[str, Any]:
    """Compare three EAC methods; missing/invalid values remain unassessed.

    CPI forecast: AC + (BAC-EV)/CPI.
    Budget-performance forecast: AC + (BAC-EV).
    CPI×SPI forecast: AC + (BAC-EV)/(CPI×SPI).
    These are scenarios, not commitments or probabilistic forecasts.
    """
    threshold = _finite_nonnegative(warning_threshold_pct, "warning_threshold_pct")
    if threshold is None:
        raise ValueError("warning_threshold_pct must be finite and non-negative")
    pv = _finite_nonnegative(evm.get("PV"), "PV")
    ev = _finite_nonnegative(evm.get("EV"), "EV")
    ac = _finite_nonnegative(evm.get("AC"), "AC")
    bac = _finite_nonnegative(evm.get("BAC"), "BAC")
    currency = str(evm.get("currency", "")).strip().upper()
    gaps = [key for key, value in (("PV", pv), ("EV", ev), ("AC", ac), ("BAC", bac)) if value is None]
    if not currency:
        gaps.append("CURRENCY")
    if gaps:
        return {"status": "INSUFFICIENT_DATA", "currency": currency, "data_gaps": gaps,
                "scenarios": [], "warning_threshold_pct": threshold}
    if bac <= 0 or pv <= 0:
        return {"status": "INSUFFICIENT_DATA", "currency": currency,
                "data_gaps": ["BAC_AND_PV_MUST_BE_POSITIVE"],
                "scenarios": [], "warning_threshold_pct": threshold}
    # AC=0 is valid evidence (for example, work not yet invoiced), but CPI
    # cannot be calculated from it. Keep the budget-rate scenario available
    # while marking CPI-based scenarios as unassessed.
    cpi = ev / ac if ac > 0 else None
    spi = ev / pv
    gaps = []
    if cpi is not None and not math.isfinite(cpi):
        gaps.append("CPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE")
    if not math.isfinite(spi):
        gaps.append("SPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE")
    if gaps:
        return {
            "status": "INSUFFICIENT_DATA", "currency": currency,
            "data_gaps": gaps, "scenarios": [],
            "warning_threshold_pct": threshold,
        }
    remaining_budget = bac - ev
    if remaining_budget < 0:
        return {"status": "REVIEW_REQUIRED", "currency": currency,
                "data_gaps": ["EV_EXCEEDS_BAC"], "scenarios": [],
                "warning_threshold_pct": threshold}
    candidates = [
        ("CPI", ac + remaining_budget / cpi if cpi is not None and cpi > 0 else None,
         "AC + (BAC - EV) / CPI"),
        ("BUDGET_RATE", ac + remaining_budget,
         "AC + (BAC - EV); remaining work at original budget rate"),
        ("CPI_X_SPI", (
            ac + remaining_budget / (cpi * spi)
            if cpi is not None and cpi > 0 and spi > 0 and math.isfinite(cpi * spi) and cpi * spi > 0
            else None
        ),
         "AC + (BAC - EV) / (CPI × SPI)"),
    ]
    scenarios = []
    for name, eac, formula in candidates:
        if eac is None or not math.isfinite(eac):
            scenarios.append({"scenario": name, "EAC": None, "ETC": None, "VAC": None,
                              "variance_pct": None, "status": "UNASSESSED", "formula": formula})
            continue
        variance = eac - bac
        variance_pct = variance / bac * 100
        if not math.isfinite(variance_pct):
            scenarios.append({"scenario": name, "EAC": None, "ETC": None, "VAC": None,
                              "variance_pct": None, "status": "UNASSESSED", "formula": formula})
            continue
        status = "OVER_BUDGET" if variance_pct > threshold else (
            "UNDER_BUDGET" if variance_pct < -threshold else "WITHIN_THRESHOLD"
        )
        scenarios.append({
            "scenario": name, "EAC": round(eac, 2), "ETC": round(eac - ac, 2),
            "VAC": round(bac - eac, 2), "variance_pct": round(variance_pct, 2),
            "status": status, "formula": formula,
        })
    assessed = [row for row in scenarios if row["EAC"] is not None]
    return {
        "status": "ASSESSED" if assessed else "INSUFFICIENT_DATA",
        "currency": currency, "cpi": round(cpi, 4) if cpi is not None else None, "spi": round(spi, 4),
        "remaining_budgeted_work": round(remaining_budget, 2),
        "warning_threshold_pct": threshold, "scenarios": scenarios,
        "limitations": [
            "Forecasts depend on the reliability and consistent valuation basis of PV, EV, AC and BAC.",
            "The CPI×SPI scenario assumes both cost and schedule performance affect remaining cost.",
            "No commitments, accruals, risk contingency, escalation, tax, change orders or probabilistic uncertainty are included.",
            "This is a decision-support scenario, not an approved revised budget.",
        ],
    }
