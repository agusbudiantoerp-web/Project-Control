"""Earned Value Management calculations from validated project workspace records.

PV and EV are sourced from progress records; AC is sourced from actual_cost.
Missing source data remains None. Forecasts are emitted only when their
mathematical inputs are available and valid.
"""
from __future__ import annotations

import math
from typing import Any


def _number(value: Any) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    try:
        value = numerator / denominator
    except (ZeroDivisionError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _sum_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_number(row.get(field)) for row in rows]
    if not values or any(value is None or value < 0 for value in values):
        return None
    try:
        total = math.fsum(values)
    except OverflowError:
        return None
    return total if math.isfinite(total) else None


def calculate_evm(
    project: dict[str, Any],
    progress_rows: list[dict[str, Any]],
    actual_cost_rows: list[dict[str, Any]],
    *,
    as_of_period: str | None = None,
) -> dict[str, Any]:
    """Calculate cumulative EVM metrics through an optional ISO-like period key."""
    project_id = str(project.get("project_id", "")).strip()
    if not project_id:
        raise ValueError("project.project_id is required")
    if not isinstance(progress_rows, list) or not isinstance(actual_cost_rows, list):
        raise TypeError("progress_rows and actual_cost_rows must be lists")

    progress = [
        dict(row) for row in progress_rows
        if str(row.get("project_id", "")).strip() == project_id
        and (as_of_period is None or str(row.get("period", "")) <= as_of_period)
    ]
    costs = [
        dict(row) for row in actual_cost_rows
        if str(row.get("project_id", "")).strip() == project_id
        and (as_of_period is None or str(row.get("period", "")) <= as_of_period)
    ]

    project_currency = str(project.get("currency", "")).strip().upper()
    progress_currency_mismatch = bool(project_currency) and any(
        str(row.get("currency", "")).strip()
        and str(row.get("currency", "")).strip().upper() != project_currency
        for row in progress
    )
    actual_cost_currency_mismatch = bool(project_currency) and any(
        str(row.get("currency", "")).strip()
        and str(row.get("currency", "")).strip().upper() != project_currency
        for row in costs
    )

    # Never combine monetary values explicitly labelled in another currency.
    pv = None if progress_currency_mismatch else _sum_field(progress, "planned_value")
    ev = None if progress_currency_mismatch else _sum_field(progress, "earned_value")
    ac = None if actual_cost_currency_mismatch else _sum_field(costs, "actual_cost")
    bac = _number(project.get("BAC", project.get("bac", project.get("budget_at_completion"))))

    spi = _safe_ratio(ev, pv) if ev is not None and pv is not None and pv > 0 else None
    cpi = _safe_ratio(ev, ac) if ev is not None and ac is not None and ac > 0 else None
    sv = ev - pv if ev is not None and pv is not None else None
    cv = ev - ac if ev is not None and ac is not None else None
    eac = _safe_ratio(bac, cpi) if bac is not None and bac > 0 and cpi is not None and cpi > 0 else None
    etc = eac - ac if eac is not None and ac is not None else None
    vac = bac - eac if bac is not None and eac is not None else None
    tcpi = (_safe_ratio(bac - ev, bac - ac)
            if bac is not None and ev is not None and ac is not None and bac > ac
            else None)

    gaps = []
    if progress_currency_mismatch:
        gaps.append("PROGRESS_CURRENCY_MISMATCH")
    if actual_cost_currency_mismatch:
        gaps.append("ACTUAL_COST_CURRENCY_MISMATCH")
    for name, value in (("PV", pv), ("EV", ev), ("AC", ac), ("BAC", bac)):
        if value is None:
            gaps.append(name)
    if bac is not None and bac <= 0:
        gaps.append("BAC_MUST_BE_POSITIVE_FOR_FORECAST")
    if pv is not None and pv <= 0:
        gaps.append("PV_MUST_BE_POSITIVE_FOR_SPI")
    if ac is not None and ac <= 0:
        gaps.append("AC_MUST_BE_POSITIVE_FOR_CPI")
    if ev is not None and pv is not None and pv > 0 and spi is None:
        gaps.append("SPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE")
    if ev is not None and ac is not None and ac > 0 and cpi is None:
        gaps.append("CPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE")
    if cpi is not None and cpi <= 0:
        gaps.append("CPI_MUST_BE_POSITIVE_FOR_EAC")
    if bac is not None and bac > 0 and cpi is not None and cpi > 0 and eac is None:
        gaps.append("EAC_EXCEEDS_SUPPORTED_NUMERIC_RANGE")
    if bac is not None and ev is not None and ac is not None and bac > ac and tcpi is None:
        gaps.append("TCPI_EXCEEDS_SUPPORTED_NUMERIC_RANGE")

    def rounded(value: float | None) -> float | None:
        return round(value, 2) if value is not None else None

    return {
        "project_id": project_id,
        "as_of_period": as_of_period,
        "source_record_counts": {"progress": len(progress), "actual_cost": len(costs)},
        "PV": rounded(pv), "EV": rounded(ev), "AC": rounded(ac), "BAC": rounded(bac),
        "SV": rounded(sv), "CV": rounded(cv), "SPI": rounded(spi), "CPI": rounded(cpi),
        "EAC": rounded(eac), "ETC": rounded(etc), "VAC": rounded(vac), "TCPI": rounded(tcpi),
        "status": "ASSESSED" if not gaps else "INSUFFICIENT_DATA",
        "data_gaps": gaps,
        "currency": str(project.get("currency", "")).strip().upper(),
        "method": {
            "SPI": "EV / PV",
            "CPI": "EV / AC",
            "EAC": "BAC / CPI (assumes current cost efficiency continues)",
            "ETC": "EAC - AC",
            "VAC": "BAC - EAC",
            "TCPI": "(BAC - EV) / (BAC - AC), when BAC > AC",
        },
        "limitations": [
            "Progress records must contain cumulative or period values consistently; this function sums supplied rows.",
            "If records are periodic deltas, summing them is appropriate; if they are cumulative snapshots, callers must select only the latest snapshot per activity.",
            "EAC is a simple CPI-based forecast and does not model remaining schedule, risk, commitments or change orders.",
            "Missing PV, EV, AC or BAC is not treated as zero.",
        ],
    }
