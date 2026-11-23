"""Integrated project intelligence from portfolio performance and risk evidence.

This deterministic layer joins existing scorecard, risk and director-priority
engines by project ID. It does not infer missing indicators or issue approvals.
"""
from __future__ import annotations

from typing import Any, Iterable

try:
    from .portfolio_performance import build_portfolio_scorecard
    from .portfolio_risk_engine import rank_portfolio
    from .project_director_decision_matrix import build_decision_matrix
except ImportError:  # Support Streamlit execution with ai_project_control as working directory.
    from portfolio_performance import build_portfolio_scorecard
    from portfolio_risk_engine import rank_portfolio
    from project_director_decision_matrix import build_decision_matrix


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def build_integrated_project_intelligence(
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Join EVM scorecard, risk ranking and director review priority."""
    source = [dict(row) for row in records]
    ids = [str(row.get("project_id", "")).strip() for row in source]
    if any(not project_id for project_id in ids):
        raise ValueError("project_id is required for every portfolio record")
    if len(ids) != len(set(ids)):
        raise ValueError("project_id values must be unique")

    risk_inputs = []
    for row in source:
        forecast_variance = _finite(row.get("forecast_variance_pct"))
        bac = _finite(row.get("BAC"))
        eac = _finite(row.get("EAC"))
        if forecast_variance is None and bac is not None and eac is not None and bac > 0:
            forecast_variance = (eac - bac) / bac * 100
        risk_inputs.append({
            "project_id": row.get("project_id"),
            "project_name": row.get("project_name"),
            "spi": row.get("SPI"),
            "cpi": row.get("CPI"),
            "total_float_days": row.get("total_float_days"),
            "risk_exposure": row.get("risk_exposure"),
            "risk_capacity": row.get("risk_capacity"),
            "forecast_variance_pct": forecast_variance,
            "currency": row.get("currency"),
        })
    risk_rows = rank_portfolio(risk_inputs)
    risk_by_id = {row["project_id"]: row for row in risk_rows}

    director_inputs = []
    for row in source:
        risk = risk_by_id.get(str(row["project_id"]), {})
        director_inputs.append({
            "project_id": row.get("project_id"),
            "project_name": row.get("project_name"),
            "SPI": row.get("SPI"),
            "CPI": row.get("CPI"),
            "risk_score": risk.get("risk_score"),
            "overloaded_resource_days": row.get("overloaded_resource_days"),
        })
    decision_result = build_decision_matrix(director_inputs)
    scorecard_inputs = []
    for row in source:
        score_record = dict(row)
        if score_record.get("budget_at_completion") in (None, ""):
            score_record["budget_at_completion"] = score_record.get("EAC")
        scorecard_inputs.append(score_record)
    scorecard = build_portfolio_scorecard(scorecard_inputs)
    score_by_id = {row["project_id"]: row for row in scorecard["projects"]}

    integrated = []
    for decision in decision_result["decisions"]:
        project_id = decision["project_id"]
        risk = risk_by_id.get(project_id, {})
        performance = score_by_id.get(project_id, {})
        integrated.append({
            **decision,
            "performance_score": performance.get("performance_score"),
            "performance_status": performance.get("status", "INSUFFICIENT_DATA"),
            "schedule_state": performance.get("schedule_state"),
            "cost_state": performance.get("cost_state"),
            "risk_status": risk.get("risk_status", "DATA_INCOMPLETE"),
            "risk_indicators": risk.get("available_indicators", []),
            "risk_missing_indicators": risk.get("missing_indicators", []),
            "risk_evidence": risk.get("evidence", []),
            "recommended_attention": risk.get("recommended_attention"),
        })

    return {
        "projects": integrated,
        "summary": {
            **decision_result["summary"],
            "assessed_performance_count": scorecard["summary"]["assessed_count"],
            "insufficient_performance_data_count": scorecard["summary"]["insufficient_data_count"],
            "critical_risk_count": sum(row["risk_status"] == "CRITICAL" for row in integrated),
            "high_risk_count": sum(row["risk_status"] == "HIGH" for row in integrated),
            "incomplete_risk_count": sum(row["risk_status"] == "DATA_INCOMPLETE" for row in integrated),
            "budget_by_currency": scorecard["summary"]["budget_by_currency"],
        },
        "methods": {
            "performance": scorecard["scoring_method"],
            "risk": (
                "Risk engine uses available SPI, CPI, total float, risk exposure/capacity "
                "and forecast variance indicators; missing indicators remain visible."
            ),
            "priority": decision_result["method"],
        },
        "limitations": [
            "Only supplied project records are included.",
            "Risk and performance scores use different scales and must not be compared as equivalent metrics.",
            "Missing metrics are not treated as zero or as evidence of good performance.",
            "Priority bands support management review and do not authorize recovery, spending or contract changes.",
        ],
    }
