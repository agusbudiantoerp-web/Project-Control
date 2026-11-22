"""Portfolio-level early-warning analytics for AI Project Control.

The engine is deterministic and provider-independent. It ranks projects using
reported schedule/cost performance and explicit risk exposure; it does not
invent missing values or combine monetary amounts across currencies.
"""
from __future__ import annotations

from typing import Any, Iterable


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _band(score: float) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 40:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    return "LOW"


def assess_project(project: dict[str, Any]) -> dict[str, Any]:
    """Assess one project. Optional fields: spi, cpi, total_float_days,
    risk_exposure, risk_capacity, forecast_variance_pct, project_id/name.
    risk_exposure and risk_capacity must use the same unit/currency.
    """
    spi = _number(project.get("spi"))
    cpi = _number(project.get("cpi"))
    total_float = _number(project.get("total_float_days"))
    exposure = _number(project.get("risk_exposure"))
    capacity = _number(project.get("risk_capacity"))
    variance = _number(project.get("forecast_variance_pct"))

    components: list[tuple[str, float]] = []
    evidence: list[str] = []

    if spi is not None:
        # SPI <= 0.80 reaches the maximum schedule component.
        components.append(("schedule", max(0.0, min(100.0, (1.0 - spi) / 0.20 * 100))))
        if spi < 1:
            evidence.append(f"SPI {spi:.2f} below 1.00")
    if cpi is not None:
        components.append(("cost", max(0.0, min(100.0, (1.0 - cpi) / 0.20 * 100))))
        if cpi < 1:
            evidence.append(f"CPI {cpi:.2f} below 1.00")
    if total_float is not None:
        components.append(("float", max(0.0, min(100.0, (10.0 - total_float) / 10.0 * 100))))
        if total_float <= 5:
            evidence.append(f"Total float {total_float:g} days (low float)")
    if exposure is not None and capacity is not None and capacity > 0:
        ratio = exposure / capacity
        components.append(("risk", max(0.0, min(100.0, ratio * 100))))
        if ratio >= 0.75:
            evidence.append(f"Risk exposure uses {ratio:.0%} of risk capacity")
    if variance is not None:
        components.append(("forecast", max(0.0, min(100.0, variance / 20.0 * 100))))
        if variance > 0:
            evidence.append(f"Forecast variance +{variance:.1f}%")

    score = sum(value for _, value in components) / len(components) if components else None
    status = _band(score) if score is not None else "DATA_INCOMPLETE"
    return {
        "project_id": str(project.get("project_id") or project.get("id") or ""),
        "project_name": str(project.get("project_name") or project.get("name") or "Unnamed project"),
        "risk_score": round(score, 1) if score is not None else None,
        "risk_status": status,
        "available_indicators": [name for name, _ in components],
        "evidence": evidence,
        "missing_indicators": [
            name for name, value in (
                ("SPI", spi), ("CPI", cpi), ("Total Float", total_float),
                ("Risk Exposure/Capacity", exposure if exposure is not None and capacity is not None and capacity > 0 else None),
                ("Forecast Variance", variance),
            ) if value is None
        ],
        "currency": project.get("currency"),
        "recommended_attention": (
            "Immediate management review" if status == "CRITICAL"
            else "Prepare corrective action" if status == "HIGH"
            else "Monitor next reporting period" if status in ("MEDIUM", "LOW")
            else "Complete project performance data"
        ),
    }


def rank_portfolio(projects: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return highest-risk projects first; incomplete records appear last."""
    assessed = [assess_project(project) for project in projects]
    return sorted(
        assessed,
        key=lambda item: (
            item["risk_score"] is None,
            -(item["risk_score"] if item["risk_score"] is not None else -1),
            item["project_name"].casefold(),
        ),
    )
