"""Separate cost and schedule risk outlooks in one executive result.

The two Monte Carlo models are reported side by side. Their percentiles are
marginal results and must not be interpreted as a joint cost/schedule scenario.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .risk_cost_simulation import build_risk_cost_simulation
from .schedule_risk_simulation import simulate_schedule_risk


def build_risk_adjusted_project_outlook(
    *,
    base_cost: float,
    currency: str,
    cost_risks: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    schedule_risks: list[dict[str, Any]],
    project_start_date: str | date,
    iterations: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    """Build distinct cost and schedule risk distributions for executive review."""
    cost = build_risk_cost_simulation(
        cost_risks, base_cost, currency, iterations=iterations, seed=seed
    )
    schedule = simulate_schedule_risk(
        activities, schedule_risks, project_start_date,
        iterations=iterations, seed=seed,
    )

    assessed = cost.get("status") == "ASSESSED" and schedule.get("status") == "ASSESSED"
    partial = cost.get("status") == "ASSESSED" or schedule.get("status") == "ASSESSED"
    status = "ASSESSED" if assessed else "PARTIALLY_ASSESSED" if partial else "INSUFFICIENT_DATA"

    return {
        "status": status,
        "currency": cost.get("currency", str(currency or "").strip().upper() or None),
        "cost_outlook": cost,
        "schedule_outlook": schedule,
        "executive_summary": {
            "cost_p50": cost.get("p50_cost"),
            "cost_p80": cost.get("p80_cost"),
            "cost_p90": cost.get("p90_cost"),
            "p80_contingency": cost.get("p80_contingency"),
            "finish_p50": schedule.get("finish_date", {}).get("p50"),
            "finish_p80": schedule.get("finish_date", {}).get("p80"),
            "finish_p90": schedule.get("finish_date", {}).get("p90"),
        },
        "interpretation": [
            "Cost and schedule are separate marginal Monte Carlo distributions.",
            "Matching iteration counts and seeds do not create a joint correlated simulation.",
            "Do not add cost and schedule percentiles or infer a probability of meeting both targets.",
            "P80 contingency is an analytical estimate, not an approved reserve.",
            "All dates use calendar days; working calendars and resource constraints are excluded.",
        ],
    }
