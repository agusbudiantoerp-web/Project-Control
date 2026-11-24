"""Risk register assessment and reproducible Monte Carlo cost contingency model."""
from __future__ import annotations

import math
import random
from statistics import mean
from typing import Any


def _number(row: dict[str, Any], field: str, risk_id: str) -> float:
    raw = row.get(field)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{risk_id}: {field} must be numeric") from None
    if not math.isfinite(value):
        raise ValueError(f"{risk_id}: {field} must be finite")
    return value


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def build_risk_cost_simulation(
    risks: list[dict[str, Any]],
    base_cost: float,
    currency: str,
    *,
    iterations: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate independent risk events with triangular cost impact distributions.

    probability must be a fraction from 0 to 1. Cost impacts are non-negative
    magnitudes; risk_type THREAT adds cost and OPPORTUNITY reduces it.
    """
    if not isinstance(risks, list) or any(not isinstance(row, dict) for row in risks):
        raise TypeError("risks must be a list of records")
    try:
        base = float(base_cost)
    except (TypeError, ValueError):
        raise ValueError("base_cost must be numeric") from None
    if not math.isfinite(base) or base < 0:
        raise ValueError("base_cost must be finite and non-negative")
    currency = str(currency or "").strip().upper()
    if not currency:
        return {"status": "INSUFFICIENT_DATA", "reason": "Project currency is required",
                "risk_count": len(risks), "scenarios": []}
    if not isinstance(iterations, int) or iterations < 1000 or iterations > 200000:
        raise ValueError("iterations must be an integer from 1000 to 200000")
    if not risks:
        return {"status": "NO_RISKS", "currency": currency, "risk_count": 0,
                "scenarios": [], "risk_register": [],
                "message": "No risk records are stored; this is not evidence of zero project risk."}

    parsed = []
    seen = set()
    for index, row in enumerate(risks):
        risk_id = str(row.get("risk_id", "")).strip()
        if not risk_id:
            raise ValueError(f"Risk row {index + 1}: risk_id is required")
        if risk_id in seen:
            raise ValueError(f"{risk_id}: duplicate risk_id")
        seen.add(risk_id)
        probability = _number(row, "probability", risk_id)
        low = _number(row, "cost_impact_min", risk_id)
        mode = _number(row, "cost_impact_most_likely", risk_id)
        high = _number(row, "cost_impact_max", risk_id)
        if not 0 <= probability <= 1:
            raise ValueError(f"{risk_id}: probability must be between 0 and 1")
        if min(low, mode, high) < 0 or not low <= mode <= high:
            raise ValueError(f"{risk_id}: impacts must satisfy 0 <= min <= most_likely <= max")
        risk_type = str(row.get("risk_type", "THREAT")).strip().upper()
        if risk_type not in {"THREAT", "OPPORTUNITY"}:
            raise ValueError(f"{risk_id}: risk_type must be THREAT or OPPORTUNITY")
        row_currency = str(row.get("currency") or currency).strip().upper()
        if row_currency != currency:
            raise ValueError(f"{risk_id}: currency {row_currency} differs from project currency {currency}")
        parsed.append({
            "risk_id": risk_id,
            "activity_id": str(row.get("activity_id", "")).strip(),
            "wbs_id": str(row.get("wbs_id", "")).strip(),
            "description": str(row.get("description", "")).strip(),
            "risk_type": risk_type,
            "probability": probability,
            "cost_impact_min": low,
            "cost_impact_most_likely": mode,
            "cost_impact_max": high,
            # Triangular expected value is (min + mode + max) / 3.
            # Use that value for prioritization, not the mode alone.
            "expected_cost_impact": probability * ((low + mode + high) / 3)
            * (1 if risk_type == "THREAT" else -1),
        })

    ranked = sorted(parsed, key=lambda row: abs(row["expected_cost_impact"]), reverse=True)
    rng = random.Random(seed)
    totals = []
    for _ in range(iterations):
        total = base
        for risk in parsed:
            if rng.random() < risk["probability"]:
                impact = rng.triangular(
                    risk["cost_impact_min"],
                    risk["cost_impact_max"],
                    risk["cost_impact_most_likely"],
                )
                total += impact if risk["risk_type"] == "THREAT" else -impact
        totals.append(max(0.0, total))

    p50 = _percentile(totals, 0.50)
    p80 = _percentile(totals, 0.80)
    p90 = _percentile(totals, 0.90)
    # Derive contingency from the displayed (rounded) P80 so the published
    # figures reconcile exactly at the report's two-decimal precision.
    contingency = max(0.0, round(p80, 2) - base)
    return {
        "status": "ASSESSED",
        "currency": currency,
        "base_cost": round(base, 2),
        "iterations": iterations,
        "seed": seed,
        "risk_count": len(parsed),
        "mean_cost": round(mean(totals), 2),
        "p50_cost": round(p50, 2),
        "p80_cost": round(p80, 2),
        "p90_cost": round(p90, 2),
        "p80_contingency": contingency,
        "probability_over_base": round(sum(value > base for value in totals) / iterations * 100, 2),
        "risk_register": [
            {**row, "expected_cost_impact": round(row["expected_cost_impact"], 2)}
            for row in ranked
        ],
        "limitations": [
            "Risk events are modeled as independent; correlations and common-cause events are not represented.",
            "Each impact uses a triangular distribution and probability is supplied as a fraction from 0 to 1.",
            "Cost impacts are additive; schedule effects, escalation, tax, currency movements and risk interactions are excluded.",
            "P80 contingency is max(0, P80 minus base cost), not an approved reserve or guarantee.",
            "Quality depends on a complete, calibrated risk register and a defensible base cost.",
        ],
    }
