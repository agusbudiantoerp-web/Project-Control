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
    progress_mode: str = "period_deltas",
) -> dict[str, Any]:
    """Calculate cumulative EVM metrics through an optional ISO-like period key."""
    project_id = str(project.get("project_id", "")).strip()
    if not project_id:
        raise ValueError("project.project_id is required")
    if not isinstance(progress_rows, list) or not isinstance(actual_cost_rows, list):
        raise TypeError("progress_rows and actual_cost_rows must be lists")
    if not isinstance(progress_mode, str) or progress_mode not in {"period_deltas", "cumulative_snapshots"}:
        raise ValueError("progress_mode must be 'period_deltas' or 'cumulative_snapshots'")

    cutoff_key = None
    if as_of_period is not None:
        cutoff_key = str(as_of_period).strip()
        if len(cutoff_key) == 7 and cutoff_key[4] == "-":
            cutoff_key += "\uffff"
    progress = [
        dict(row) for row in progress_rows
        if str(row.get("project_id", "")).strip() == project_id
        and (cutoff_key is None or str(row.get("period", "")).strip() <= cutoff_key)
    ]
    costs = [
        dict(row) for row in actual_cost_rows
        if str(row.get("project_id", "")).strip() == project_id
        and (cutoff_key is None or str(row.get("period", "")).strip() <= cutoff_key)
    ]
    progress_mode_gap = None
    if progress_mode == "cumulative_snapshots" and progress:
        if any(not str(row.get("activity_id", "")).strip() or not str(row.get("period", "")).strip() for row in progress):
            progress = []
            progress_mode_gap = "CUMULATIVE_PROGRESS_REQUIRES_ACTIVITY_ID_AND_PERIOD"
        else:
            latest_by_activity = {}
            for row in progress:
                activity_id = str(row["activity_id"]).strip()
                period = str(row["period"]).strip()
                previous = latest_by_activity.get(activity_id)
                if previous is None or period > str(previous.get("period", "")):
                    latest_by_activity[activity_id] = row
            progress = list(latest_by_activity.values())

    pv = _sum_field(progress, "planned_value")
    ev = _sum_field(progress, "earned_value")
    ac = _sum_field(costs, "actual_cost")
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
    if progress_mode_gap:
        gaps.append(progress_mode_gap)
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
        "progress_mode": progress_mode,
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
            "progress_mode=period_deltas sums supplied period values; use it only when each row is a period increment.",
            "progress_mode=cumulative_snapshots selects the latest available progress row per activity through the as-of period before summing PV and EV.",
            "Actual-cost rows are summed as transactions/period deltas in either progress mode; do not supply cumulative AC snapshots.",
            "EAC is a simple CPI-based forecast and does not model remaining schedule, risk, commitments or change orders.",
            "Missing PV, EV, AC or BAC is not treated as zero.",
        ],
    }
