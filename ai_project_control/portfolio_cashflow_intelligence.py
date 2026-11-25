"""Portfolio cash-flow and cost burn analysis with currency-safe aggregation."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def build_portfolio_cashflow_view(project_finance: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(project_finance, list) or any(not isinstance(row, dict) for row in project_finance):
        raise TypeError("project_finance must be a list of dictionaries")
    by_project: dict[str, dict[str, Any]] = {}
    by_currency: dict[str, dict[str, float]] = defaultdict(lambda: {
        "budget": 0.0, "actual_cost": 0.0, "remaining_budget": 0.0
    })
    unassessed = []
    seen_project_ids: set[str] = set()
    for item in project_finance:
        project_id = str(item.get("project_id", "")).strip()
        if not project_id:
            raise ValueError("project_id is required")
        if project_id in seen_project_ids:
            raise ValueError(f"duplicate project finance record: {project_id}")
        seen_project_ids.add(project_id)
        currency = str(item.get("currency", "")).strip().upper()
        if not currency:
            unassessed.append({"project_id": project_id, "reason": "Project currency missing"})
            continue
        if isinstance(item.get("budget"), bool) or isinstance(item.get("actual_cost"), bool):
            unassessed.append({"project_id": project_id, "reason": "Budget or actual cost must not be boolean"})
            continue
        try:
            budget = float(item.get("budget"))
            actual = float(item.get("actual_cost"))
        except (TypeError, ValueError):
            unassessed.append({"project_id": project_id, "reason": "Budget or actual cost missing/non-numeric"})
            continue
        if not math.isfinite(budget) or budget < 0 or not math.isfinite(actual) or actual < 0:
            unassessed.append({"project_id": project_id, "reason": "Budget or actual cost invalid"})
            continue
        remaining = budget - actual
        utilization = (actual / budget * 100.0) if budget > 0 else None
        row = {
            "project_id": project_id,
            "project_name": str(item.get("project_name", "")),
            "currency": currency,
            "budget": round(budget, 2),
            "actual_cost": round(actual, 2),
            "remaining_budget": round(remaining, 2),
            "cost_utilization_pct": round(utilization, 2) if utilization is not None else None,
            "status": "OVER_BUDGET" if remaining < 0 else "WITHIN_BUDGET",
        }
        by_project[project_id] = row
        totals = by_currency[currency]
        totals["budget"] += budget
        totals["actual_cost"] += actual
        totals["remaining_budget"] += remaining
        if not all(math.isfinite(totals[key]) for key in ("budget", "actual_cost", "remaining_budget")):
            raise ValueError(f"Portfolio financial totals exceed the supported numeric range for {currency}")

    totals = {
        currency: {key: round(value, 2) for key, value in values.items()}
        for currency, values in sorted(by_currency.items())
    }
    return {
        "status": "ASSESSED" if by_project else "INSUFFICIENT_DATA",
        "project_count_assessed": len(by_project),
        "project_count_unassessed": len(unassessed),
        "projects_over_budget": sum(row["status"] == "OVER_BUDGET" for row in by_project.values()),
        "totals_by_currency": totals,
        "projects": sorted(by_project.values(), key=lambda row: (row["currency"], row["project_id"])),
        "unassessed_projects": unassessed,
        "limitations": [
            "Actual cost is summed from the supplied actual-cost records; periods are not extrapolated into a forecast.",
            "Budget is taken from the supplied project BAC or BOQ amount and is not silently mixed with actual commitments.",
            "Negative remaining budget indicates actual cost exceeds the supplied budget; it is not a cash balance.",
            "Totals are grouped by currency; no foreign-exchange conversion or consolidated base currency is assumed.",
        ],
    }
