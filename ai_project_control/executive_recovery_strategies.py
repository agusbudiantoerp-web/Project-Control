"""Evidence-led executive recovery strategy alternatives."""
from __future__ import annotations

from typing import Any
import pandas as pd


def build_executive_recovery_strategies(
    portfolio: pd.DataFrame,
    risk_register: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Generate ranked strategy options without inventing quantified benefits."""
    empty = pd.DataFrame()
    if not isinstance(portfolio, pd.DataFrame) or portfolio.empty:
        return {"available": False, "strategies": empty, "project_summary": empty,
                "assumptions": ["No portfolio records are available."]}
    if {"project_id", "project_name"} - set(portfolio.columns):
        return {"available": False, "strategies": empty, "project_summary": empty,
                "assumptions": ["project_id and project_name are required."]}

    data = portfolio.copy()
    for col in ("SPI", "CPI", "schedule_slip_days", "BAC", "EAC"):
        if col not in data:
            data[col] = pd.NA
        data[col] = pd.to_numeric(data[col], errors="coerce")
    if "currency" not in data:
        data["currency"] = None
    if isinstance(risk_register, pd.DataFrame) and not risk_register.empty and "project_id" in risk_register:
        risk_cols = [c for c in ("project_id", "risk_score", "risk_status", "evidence", "recommended_attention") if c in risk_register]
        data = data.merge(risk_register[risk_cols].drop_duplicates("project_id"), on="project_id", how="left")
    else:
        data["risk_score"] = pd.NA
        data["risk_status"] = "UNSCORED"
        data["evidence"] = None
        data["recommended_attention"] = None
    data["risk_score"] = pd.to_numeric(data["risk_score"], errors="coerce")
    data["cost_variance_pct"] = (data["EAC"] - data["BAC"]) / data["BAC"].where(data["BAC"] > 0) * 100

    rows = []
    for _, p in data.iterrows():
        spi, cpi, slip, risk, cv = (p.get("SPI"), p.get("CPI"), p.get("schedule_slip_days"), p.get("risk_score"), p.get("cost_variance_pct"))
        schedule_issue = pd.notna(spi) and spi < 1 or pd.notna(slip) and slip > 0
        cost_issue = pd.notna(cpi) and cpi < 1 or pd.notna(cv) and cv > 0
        risk_issue = pd.notna(risk) and risk >= 40
        specs = [
            ("Schedule recovery", "Schedule", schedule_issue,
             "Validate critical path, constraints, remaining durations and near-critical paths; prepare a time-phased recovery baseline.",
             "Activities, logic, calendars, remaining duration, float, approved work windows",
             "Potential schedule recovery; days saved require CPM what-if and field validation.",
             "Acceleration can increase cost, fatigue, safety exposure or downstream congestion."),
            ("Cost recovery", "Cost", cost_issue,
             "Reconcile actuals, commitments, quantities and estimate-to-complete; identify cost drivers and accountable owners.",
             "BOQ, actual cost, commitments, forecast method, currency and approved change log",
             "Potential cost containment; savings require validated quantities and cost rates.",
             "Cost reduction must not compromise scope, quality, safety or contractual obligations."),
            ("Resource reallocation", "Resource", schedule_issue or risk_issue,
             "Review shared-resource availability, donor-project impact, competence, mobilization and date compatibility.",
             "Resource IDs, shared_resource_id, daily demand, capacity, calendars and assignment dates",
             "Potential bottleneck relief; schedule effect requires resource-loaded CPM simulation.",
             "A donor project may incur delay; no transfer should be approved from this screening alone."),
            ("Risk mitigation", "Risk", risk_issue or schedule_issue or cost_issue,
             "Assign risk owner, response, trigger, due date, contingency and residual-risk review.",
             "Risk register with probability, impact, response cost, owner and due date",
             "Potential reduction in exposure; residual risk must be reassessed after action.",
             "Risk score alone is not a quantified probability of failure or guaranteed loss avoidance."),
            ("Integrated recovery", "Integrated", schedule_issue and cost_issue or risk_issue and (schedule_issue or cost_issue),
             "Coordinate schedule, cost, resource and risk actions in one approved recovery plan with weekly gates.",
             "Complete CPM, EVM, resource-loaded schedule, cost forecast and current risk register",
             "Potential combined improvement; benefits and trade-offs require an integrated what-if model.",
             "Avoid double-counting benefits across schedule, cost, resource and risk actions."),
        ]
        project_id = str(p["project_id"])
        for name, category, triggered, action, required, benefit, caveat in specs:
            if not triggered:
                continue
            evidence = []
            if pd.notna(spi) and spi < 1: evidence.append(f"SPI {spi:.2f} below 1.00")
            if pd.notna(cpi) and cpi < 1: evidence.append(f"CPI {cpi:.2f} below 1.00")
            if pd.notna(slip) and slip > 0: evidence.append(f"Forecast slip {slip:.0f} days")
            if pd.notna(cv) and cv > 0: evidence.append(f"EAC variance +{cv:.1f}%")
            if pd.notna(risk) and risk >= 40: evidence.append(f"Risk score {risk:.1f}")
            # Readiness is explicitly data-based, not a claimed feasibility probability.
            checks = {
                "Schedule": ["activities", "logic", "calendars", "remaining duration"],
                "Cost": ["BOQ", "actual cost", "commitments", "ETC"],
                "Resource": ["shared resource identity", "daily demand", "capacity", "calendar"],
                "Risk": ["risk probability", "impact", "owner", "response due date"],
                "Integrated": ["CPM", "EVM", "resource loading", "risk register"],
            }[category]
            readiness = "Requires validation"
            if category == "Schedule" and pd.notna(spi) and pd.notna(slip): readiness = "Partially evidenced"
            if category == "Cost" and pd.notna(cpi) and pd.notna(cv): readiness = "Partially evidenced"
            if category == "Risk" and pd.notna(risk): readiness = "Partially evidenced"
            rows.append({
                "project_id": project_id, "project_name": str(p["project_name"]),
                "currency": p.get("currency"), "strategy": name, "category": category,
                "trigger_evidence": "; ".join(evidence) or "Risk / performance trigger",
                "risk_score": risk, "SPI": spi, "CPI": cpi,
                "schedule_slip_days": slip, "cost_variance_pct": cv,
                "readiness": readiness, "required_data_to_validate": ", ".join(checks),
                "recommended_action": action, "potential_benefit_not_quantified": benefit,
                "trade_off_and_control": caveat,
            })
    strategies = pd.DataFrame(rows)
    if strategies.empty:
        return {"available": True, "strategies": strategies,
                "project_summary": pd.DataFrame(columns=["project_id", "project_name", "strategy_count", "top_action"]),
                "assumptions": ["No recovery trigger was found in the available portfolio indicators. This does not prove that projects are free of risk."]}
    category_order = {"Integrated": 0, "Schedule": 1, "Cost": 2, "Resource": 3, "Risk": 4}
    strategies["_order"] = strategies["category"].map(category_order).fillna(9)
    strategies = strategies.sort_values(["project_id", "_order"]).drop(columns="_order").reset_index(drop=True)
    project_summary = strategies.groupby(["project_id", "project_name"], as_index=False).agg(
        strategy_count=("strategy", "count"),
        top_action=("recommended_action", "first"),
        trigger_evidence=("trigger_evidence", lambda values: " | ".join(dict.fromkeys(values))),
    )
    return {
        "available": True, "strategies": strategies, "project_summary": project_summary,
        "assumptions": [
            "Strategies are triggered only by adverse indicators present in the supplied portfolio and risk register.",
            "No schedule days, cost savings, probabilities or productivity gains are fabricated; quantified benefits require a separate validated what-if model.",
            "Resource transfer requires explicit shared resource identity, compatible units, dates, calendars and donor impact review.",
            "Integrated recovery is suggested only when schedule and cost indicators, or risk plus either schedule or cost indicators, justify coordinated action.",
            "All recommendations require accountable owner, approval, safety/quality review and baseline/change-control governance.",
            "Missing data means not yet validated; it does not mean the strategy is infeasible or the project is healthy.",
        ],
    }
