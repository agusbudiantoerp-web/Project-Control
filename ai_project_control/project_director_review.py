"""Project Director review synthesis from explicit project-control evidence."""
from __future__ import annotations

from typing import Any

from .project_director_decision_matrix import build_decision_matrix


def build_project_director_review(
    project: dict[str, Any],
    evm: dict[str, Any],
    *,
    risk_simulation: dict[str, Any] | None = None,
    resource_summary: dict[str, Any] | None = None,
    schedule_forecast: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a review-priority and evidence register without inventing indicators.

    The decision matrix consumes SPI/CPI from EVM and risk_score / overloaded
    resource days only when explicitly supplied in Project Master. Other engine
    outputs are shown as separate signals and are not silently converted to scores.
    """
    record = {
        "project_id": project.get("project_id", evm.get("project_id", "")),
        "project_name": project.get("project_name", ""),
        "SPI": evm.get("SPI"),
        "CPI": evm.get("CPI"),
        "risk_score": project.get("risk_score"),
        "overloaded_resource_days": project.get("overloaded_resource_days"),
    }
    matrix = build_decision_matrix([record])
    decision = matrix["decisions"][0]
    signals: list[dict[str, Any]] = []

    if evm.get("SPI") is None:
        signals.append({"area": "SCHEDULE_PERFORMANCE", "status": "UNASSESSED",
                        "evidence": "SPI is unavailable from current EVM inputs."})
    elif evm["SPI"] < 1:
        signals.append({"area": "SCHEDULE_PERFORMANCE", "status": "ATTENTION",
                        "evidence": f"SPI is {evm['SPI']}; below 1.00."})
    else:
        signals.append({"area": "SCHEDULE_PERFORMANCE", "status": "MONITOR",
                        "evidence": f"SPI is {evm['SPI']}."})

    if evm.get("CPI") is None:
        signals.append({"area": "COST_PERFORMANCE", "status": "UNASSESSED",
                        "evidence": "CPI is unavailable from current EVM inputs."})
    elif evm["CPI"] < 1:
        signals.append({"area": "COST_PERFORMANCE", "status": "ATTENTION",
                        "evidence": f"CPI is {evm['CPI']}; below 1.00."})
    else:
        signals.append({"area": "COST_PERFORMANCE", "status": "MONITOR",
                        "evidence": f"CPI is {evm['CPI']}."})

    if schedule_forecast:
        delayed = schedule_forecast.get("delayed_activity_ids") or []
        unassessed = schedule_forecast.get("unassessed_activity_ids") or []
        signals.append({
            "area": "ACTIVITY_PROGRESS",
            "status": "ATTENTION" if delayed else "UNASSESSED" if unassessed else "MONITOR",
            "evidence": f"{len(delayed)} delayed activities; {len(unassessed)} unassessed activities.",
        })

    if resource_summary:
        overload = resource_summary.get("overloaded_count")
        unassessed = resource_summary.get("unassessed_count")
        signals.append({
            "area": "RESOURCE_CAPACITY",
            "status": "ATTENTION" if overload else "UNASSESSED" if unassessed else "MONITOR",
            "evidence": f"{overload or 0} overloaded resource-period rows; {unassessed or 0} unassessed rows.",
        })

    if risk_simulation:
        if risk_simulation.get("status") == "ASSESSED":
            probability = risk_simulation.get("probability_over_base")
            p80 = risk_simulation.get("p80_contingency")
            signals.append({
                "area": "RISK_COST",
                "status": "ATTENTION" if probability is not None and probability > 0 else "MONITOR",
                "evidence": f"Simulated probability above base cost: {probability}%; P80 contingency: {risk_simulation.get('currency')} {p80}.",
            })
        else:
            signals.append({"area": "RISK_COST", "status": "UNASSESSED",
                            "evidence": "Risk simulation is not assessed; verify the risk register and currency."})

    return {
        "status": decision["priority"],
        "decision": decision,
        "signals": signals,
        "summary": {
            "attention_count": sum(item["status"] == "ATTENTION" for item in signals),
            "unassessed_count": sum(item["status"] == "UNASSESSED" for item in signals),
            "monitor_count": sum(item["status"] == "MONITOR" for item in signals),
        },
        "governance": [
            "Priority is a screening aid, not an automated approval or instruction to change the baseline.",
            "Risk score and overloaded resource days are used in the decision matrix only when explicitly stored in Project Master.",
            "Resource-period overload counts and simulated cost exceedance probability remain separate evidence; they are not converted into risk scores or overload days.",
            "Project Director must validate source data, critical-path logic, safety, quality, contract and funding constraints before authorizing recovery.",
        ],
    }
