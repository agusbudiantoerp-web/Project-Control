"""Executive portfolio command-center decision queue.

This is a transparent screening aid, not an automated approval or a substitute
for contract, safety, engineering, or finance review.
"""
from __future__ import annotations

from typing import Any
import pandas as pd


def build_executive_command_center(
    portfolio: pd.DataFrame,
    risk_register: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Build an evidence-backed intervention queue from available portfolio KPIs."""
    empty = pd.DataFrame()
    if not isinstance(portfolio, pd.DataFrame) or portfolio.empty:
        return {"available": False, "queue": empty, "summary": empty,
                "assumptions": ["No portfolio KPI records are available."]}

    required = {"project_id", "project_name"}
    if required - set(portfolio.columns):
        return {"available": False, "queue": empty, "summary": empty,
                "assumptions": ["Portfolio data must contain project_id and project_name."]}

    data = portfolio.copy()
    for col in ("SPI", "CPI", "schedule_slip_days", "BAC", "EAC"):
        if col not in data:
            data[col] = pd.NA
        data[col] = pd.to_numeric(data[col], errors="coerce")
    if "currency" not in data:
        data["currency"] = None

    risk_cols = ["project_id", "risk_score", "risk_status", "evidence", "missing_indicators"]
    if isinstance(risk_register, pd.DataFrame) and not risk_register.empty and "project_id" in risk_register:
        available_cols = [c for c in risk_cols if c in risk_register.columns]
        risk = risk_register[available_cols].drop_duplicates("project_id", keep="first")
        data = data.merge(risk, on="project_id", how="left")
    else:
        data["risk_score"] = pd.NA
        data["risk_status"] = "UNSCORED"
        data["evidence"] = None
        data["missing_indicators"] = None

    data["risk_score"] = pd.to_numeric(data["risk_score"], errors="coerce")
    data["cost_variance_pct"] = (
        (data["EAC"] - data["BAC"]) / data["BAC"].where(data["BAC"] > 0) * 100
    )
    data["schedule_pressure"] = (data["schedule_slip_days"].clip(lower=0, upper=30) / 30 * 100)
    data["cost_pressure"] = (data["cost_variance_pct"].clip(lower=0, upper=20) / 20 * 100)
    # Weighted screening index: risk engine 60%, schedule slip 25%, cost variance 15%.
    # Missing inputs are excluded and remaining weights are renormalized.
    scores = []
    evidence_out = []
    actions_out = []
    completeness = []
    for _, row in data.iterrows():
        components = []
        if pd.notna(row["risk_score"]):
            components.append((float(row["risk_score"]), 0.60))
        if pd.notna(row["schedule_pressure"]):
            components.append((float(row["schedule_pressure"]), 0.25))
        if pd.notna(row["cost_pressure"]):
            components.append((float(row["cost_pressure"]), 0.15))
        score = (
            sum(value * weight for value, weight in components) / sum(weight for _, weight in components)
            if components else None
        )
        scores.append(round(score, 1) if score is not None else None)
        evidence = []
        actions = []
        if pd.notna(row["SPI"]) and row["SPI"] < 1:
            evidence.append(f"SPI below plan ({row['SPI']:.2f})")
            actions.append("Validate critical path and time-phased recovery plan")
        if pd.notna(row["CPI"]) and row["CPI"] < 1:
            evidence.append(f"CPI below budget efficiency ({row['CPI']:.2f})")
            actions.append("Reconcile actual cost, commitments and estimate to complete")
        if pd.notna(row["schedule_slip_days"]) and row["schedule_slip_days"] > 0:
            evidence.append(f"Forecast slip {row['schedule_slip_days']:.0f} days")
            actions.append("Review recovery options, constraints and resource feasibility")
        if pd.notna(row["cost_variance_pct"]) and row["cost_variance_pct"] > 0:
            evidence.append(f"EAC variance +{row['cost_variance_pct']:.1f}%")
            actions.append("Validate EAC drivers and cost mitigation ownership")
        prior_evidence = row.get("evidence")
        if isinstance(prior_evidence, (list, tuple)):
            evidence.extend(str(x) for x in prior_evidence if str(x) not in evidence)
        actions_out.append("; ".join(dict.fromkeys(actions)) if actions else (
            "Complete missing performance data" if score is None else
            "Maintain controls and review at next reporting period"
        ))
        evidence_out.append("; ".join(dict.fromkeys(evidence)) if evidence else "No adverse signal in available indicators")
        completeness.append(len(components))

    data["executive_priority_score"] = scores
    data["decision_evidence"] = evidence_out
    data["recommended_executive_action"] = actions_out
    data["scored_indicator_groups"] = completeness
    data["decision_tier"] = data["executive_priority_score"].apply(
        lambda s: "UNSCORED" if pd.isna(s) else
        ("P1 - IMMEDIATE" if s >= 70 else
         ("P2 - HIGH" if s >= 40 else
          ("P3 - MONITOR" if s >= 20 else "P4 - ROUTINE")))
    )
    queue = data.sort_values(
        ["executive_priority_score", "schedule_slip_days"],
        ascending=[False, False], na_position="last"
    ).reset_index(drop=True)
    summary = queue.groupby("decision_tier", dropna=False).agg(
        projects=("project_id", "count"),
        average_priority_score=("executive_priority_score", "mean"),
    ).reset_index()
    summary["average_priority_score"] = summary["average_priority_score"].round(1)
    return {
        "available": True, "queue": queue, "summary": summary,
        "assumptions": [
            "Screening index uses risk score 60%, schedule slip 25%, and positive EAC variance 15%; available components are renormalized when data is missing.",
            "Schedule pressure is capped at 30 days and cost pressure at +20% for scoring; raw values remain visible in the queue.",
            "Risk, SPI and CPI can overlap as performance signals; the index is a prioritization aid, not a probability of project failure.",
            "Financial amounts are never aggregated across currencies.",
            "UNSCORED projects require data completion and must not be interpreted as low risk.",
        ],
    }
