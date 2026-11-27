"""Compare recovery outcomes using explicit before/after evidence.

No composite score or causal claim is produced: indicators remain separate and
missing inputs stay unassessed. Monetary values must use the same currency.
"""
from __future__ import annotations

import math
from typing import Any


_METRICS = {
    "SPI": "higher",
    "CPI": "higher",
    "risk_score": "lower",
    "delayed_activity_count": "lower",
    "overdue_action_count": "lower",
}


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def evaluate_recovery_effectiveness(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    approved_recovery_budget: Any = None,
    actual_recovery_cost: Any = None,
    currency: str | None = None,
) -> dict[str, Any]:
    """Evaluate direction of KPI movement and recovery cost variance."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise TypeError("before and after must be dictionaries")
    comparisons = {}
    improved = worsened = unchanged = unassessed = 0
    for metric, preferred in _METRICS.items():
        # A metric omitted from both snapshots was not part of the assessment;
        # an explicitly supplied None/invalid value is present but unassessed.
        if metric not in before and metric not in after:
            continue
        old, new = _finite(before.get(metric)), _finite(after.get(metric))
        if old is None or new is None:
            comparisons[metric] = {
                "status": "UNASSESSED", "before": old, "after": new, "delta": None,
            }
            unassessed += 1
            continue
        delta = new - old
        if delta == 0:
            status = "UNCHANGED"
            unchanged += 1
        elif (delta > 0 and preferred == "higher") or (delta < 0 and preferred == "lower"):
            status = "IMPROVED"
            improved += 1
        else:
            status = "WORSENED"
            worsened += 1
        comparisons[metric] = {
            "status": status, "before": old, "after": new, "delta": round(delta, 4),
        }

    budget, actual = _finite(approved_recovery_budget), _finite(actual_recovery_cost)
    if budget is not None and budget < 0 or actual is not None and actual < 0:
        raise ValueError("recovery budget and cost must be non-negative")
    if budget is not None and actual is not None:
        cost_status = "WITHIN_BUDGET" if actual <= budget else "OVER_BUDGET"
        cost_variance = round(budget - actual, 2)
    else:
        cost_status, cost_variance = "UNASSESSED", None

    if not comparisons:
        outcome = "INSUFFICIENT_DATA"
    elif improved and not worsened:
        outcome = "POSITIVE_INDICATORS"
    elif worsened and not improved:
        outcome = "NEGATIVE_INDICATORS"
    elif improved and worsened:
        outcome = "MIXED_INDICATORS"
    elif unassessed == len(comparisons):
        outcome = "INSUFFICIENT_DATA"
    else:
        outcome = "NO_MEASURED_CHANGE"

    return {
        "status": outcome,
        "indicator_summary": {
            "improved": improved, "worsened": worsened,
            "unchanged": unchanged, "unassessed": unassessed,
        },
        "comparisons": comparisons,
        "recovery_cost": {
            "currency": str(currency or "").strip().upper() or None,
            "approved_budget": budget, "actual_cost": actual,
            "variance_favourable": cost_variance, "status": cost_status,
        },
        "limitations": [
            "Before/after movement does not establish that recovery actions caused the change.",
            "Compare equivalent reporting periods, scope, definitions and data sources.",
            "No weighted composite score is calculated; project leadership must assess trade-offs.",
            "Cost comparison is meaningful only when budget and actual cost use the same currency and scope.",
            "Missing or invalid indicators remain unassessed, not zero.",
        ],
    }
