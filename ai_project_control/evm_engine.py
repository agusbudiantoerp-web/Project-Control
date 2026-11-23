"""Earned Value Management calculations from validated project workspace records.

PV and EV are sourced from progress records; AC is sourced from actual_cost.
Missing source data remains None. Forecasts are emitted only when their
mathematical inputs are available and valid.
"""
from __future__ import annotations

import math
from typing import Any


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _sum_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_number(row.get(field)) for row in rows]
    if not values or any(value is None for value in values):
        return None
    return sum(values)


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

    pv = _sum_field(progress, "planned_value")
    ev = _sum_field(progress, "earned_value")
    ac = _sum_field(costs, "actual_cost")
    bac = _number(project.get("BAC", project.get("bac", project.get("budget_at_completion"))))

    spi = ev / pv if ev is not None and pv is not None and pv > 0 else None
    cpi = ev / ac if ev is not None and ac is not None and ac > 0 else None
    sv = ev - pv if ev is not None and pv is not None else None
    cv = ev - ac if ev is not None and ac is not None else None
    eac = bac / cpi if bac is not None and cpi is not None and cpi > 0 else None
    etc = eac - ac if eac is not None and ac is not None else None
    vac = bac - eac if bac is not None and eac is not None else None
    tcpi = ((bac - ev) / (bac - ac)
            if bac is not None and ev is not None and ac is not None and bac > ac
            else None)

    gaps = []
    for name, value in (("PV", pv), ("EV", ev), ("AC", ac), ("BAC", bac)):
        if value is None:
            gaps.append(name)
    if pv is not None and pv <= 0:
        gaps.append("PV_MUST_BE_POSITIVE_FOR_SPI")
    if ac is not None and ac <= 0:
        gaps.append("AC_MUST_BE_POSITIVE_FOR_CPI")
    if cpi is not None and cpi <= 0:
        gaps.append("CPI_MUST_BE_POSITIVE_FOR_EAC")

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
