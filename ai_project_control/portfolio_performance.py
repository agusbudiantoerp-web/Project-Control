"""Deterministic portfolio performance scorecard with explicit data-quality states."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable

REQUIRED_METRICS = ("SPI", "CPI")
OPTIONAL_METRICS = ("risk_score", "overloaded_resource_days", "forecast_variance_days")


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def score_project(record: dict[str, Any]) -> dict[str, Any]:
    """Score one project; missing core metrics produce INSUFFICIENT_DATA, never a safe score."""
    spi, cpi = _finite(record.get("SPI")), _finite(record.get("CPI"))
    if spi is None or cpi is None:
        return {
            "project_id": str(record.get("project_id", "")),
            "project_name": str(record.get("project_name", "")),
            "status": "INSUFFICIENT_DATA",
            "performance_score": None,
            "schedule_state": "UNASSESSED" if spi is None else _state(spi),
            "cost_state": "UNASSESSED" if cpi is None else _state(cpi),
            "data_gaps": [name for name, value in (("SPI", spi), ("CPI", cpi)) if value is None],
            "risk_score": _finite(record.get("risk_score")),
            "overloaded_resource_days": _finite(record.get("overloaded_resource_days")),
            "currency": str(record.get("currency", "")).strip().upper(),
            "budget_at_completion": _finite(record.get("budget_at_completion")),
        }

    # Transparent equal weighting: SPI and CPI are capped at 0..1.2 then normalized to 100.
    score = round(((min(max(spi, 0.0), 1.2) / 1.2) +
                   (min(max(cpi, 0.0), 1.2) / 1.2)) * 50, 2)
    risk = _finite(record.get("risk_score"))
    overload = _finite(record.get("overloaded_resource_days"))
    return {
        "project_id": str(record.get("project_id", "")),
        "project_name": str(record.get("project_name", "")),
        "status": "ASSESSED",
        "performance_score": score,
        "schedule_state": _state(spi),
        "cost_state": _state(cpi),
        "data_gaps": [],
        "risk_score": risk,
        "overloaded_resource_days": overload,
        "currency": str(record.get("currency", "")).strip().upper(),
        "budget_at_completion": _finite(record.get("budget_at_completion")),
    }


def _state(value: float) -> str:
    if value < 0.95:
        return "RED"
    if value < 1.0:
        return "AMBER"
    return "GREEN"


def build_portfolio_scorecard(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build project rows and summaries; budget totals remain separated by currency."""
    rows = [score_project(dict(item)) for item in records]
    currencies: dict[str, float] = defaultdict(float)
    for row in rows:
        amount = row["budget_at_completion"]
        currency = row["currency"]
        if amount is not None and currency:
            currencies[currency] += amount

    assessed = [row for row in rows if row["status"] == "ASSESSED"]
    ranked = sorted(
        assessed,
        key=lambda row: (
            row["performance_score"],
            -(row["risk_score"] if row["risk_score"] is not None else -1),
            row["project_id"],
        ),
    )
    return {
        "projects": rows,
        "ranked_project_ids": [row["project_id"] for row in ranked],
        "summary": {
            "project_count": len(rows),
            "assessed_count": len(assessed),
            "insufficient_data_count": len(rows) - len(assessed),
            "red_count": sum(row["schedule_state"] == "RED" or row["cost_state"] == "RED" for row in assessed),
            "amber_count": sum(row["schedule_state"] == "AMBER" or row["cost_state"] == "AMBER" for row in assessed),
            "green_count": sum(row["schedule_state"] == "GREEN" and row["cost_state"] == "GREEN" for row in assessed),
            "budget_by_currency": dict(sorted(currencies.items())),
        },
        "scoring_method": "Equal-weight SPI/CPI; each capped to [0, 1.2], then normalized to 0-100.",
    }
