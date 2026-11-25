"""COO-facing portfolio decision brief built from existing, auditable portfolio outputs."""
from __future__ import annotations

from datetime import date
from typing import Any


def build_coo_portfolio_decision_brief(
    portfolio: dict[str, Any],
    risk_resource: dict[str, Any],
    portfolio_actions: dict[str, Any],
    *,
    as_of_date: date | str | None = None,
) -> dict[str, Any]:
    for name, value in (("portfolio", portfolio), ("risk_resource", risk_resource), ("portfolio_actions", portfolio_actions)):
        if not isinstance(value, dict):
            raise TypeError(f"{name} must be a dictionary")
    if as_of_date is None:
        cutoff = date.today()
    elif isinstance(as_of_date, date):
        cutoff = as_of_date
    else:
        try:
            cutoff = date.fromisoformat(str(as_of_date))
        except ValueError:
            raise ValueError("as_of_date must be a valid ISO date") from None

    projects = portfolio.get("projects", [])
    actions = portfolio_actions.get("actions", [])
    if not isinstance(projects, list) or not isinstance(actions, list):
        raise TypeError("portfolio projects and actions must be lists")

    decisions = []
    for row in projects:
        if not isinstance(row, dict):
            continue
        flags = []
        if row.get("priority") == "P1":
            flags.append("P1_PRIORITY")
        if row.get("schedule_status") == "DELAYED" or (row.get("delayed_activity_count") or 0) > 0:
            flags.append("SCHEDULE_DELAY")
        if row.get("resource_overloaded_count", 0):
            flags.append("RESOURCE_OVERLOAD")
        if row.get("risk_status") == "INVALID_DATA":
            flags.append("RISK_DATA_INVALID")
        if row.get("status") == "INSUFFICIENT_DATA" or row.get("priority") == "UNASSESSED":
            flags.append("INSUFFICIENT_EVM_DATA")
        if flags:
            decisions.append({
                "project_id": row.get("project_id", ""),
                "project_name": row.get("project_name", ""),
                "priority": row.get("priority", "UNASSESSED"),
                "SPI": row.get("SPI"),
                "CPI": row.get("CPI"),
                "currency": row.get("currency", ""),
                "EAC": row.get("EAC"),
                "flags": flags,
                "management_review_required": True,
            })

    action_summary = portfolio_actions.get("summary", {})
    risk_conflicts = risk_resource.get("shared_resource_conflicts", [])
    risk_rows = risk_resource.get("top_risks", [])
    currency_exposure = risk_resource.get("expected_exposure_by_currency", {})
    decisions.sort(key=lambda row: (
        0 if row["priority"] == "P1" else 1,
        -len(row["flags"]),
        str(row["project_id"]),
    ))

    recommendations = []
    if action_summary.get("overdue_count", 0):
        recommendations.append("Review overdue executive actions; confirm accountable owner, recovery date and escalation path.")
    if action_summary.get("blocked_count", 0):
        recommendations.append("Resolve blocked executive actions through the designated decision authority.")
    if risk_resource.get("shared_resource_conflict_count", 0):
        recommendations.append("Resolve shared-resource capacity conflicts with project owners before approving resource transfers or baseline changes.")
    if risk_resource.get("risk_count_unassessed", 0):
        recommendations.append("Complete missing/invalid risk probabilities, impact values and project currency before relying on portfolio exposure totals.")
    if any(row.get("priority") == "P1" for row in decisions):
        recommendations.append("Hold a focused P1 project review covering schedule, cost, risk ownership and executable recovery actions.")
    if not recommendations:
        recommendations.append("Continue routine governance reviews and capture the next portfolio snapshot.")

    return {
        "status": "ASSESSED" if portfolio.get("project_count", 0) else "NO_PROJECTS",
        "as_of_date": cutoff.isoformat(),
        "project_count": portfolio.get("project_count", 0),
        "projects_requiring_review": len(decisions),
        "projects_for_review": decisions,
        "executive_action_summary": action_summary,
        "risk_exposure_by_currency": currency_exposure,
        "top_portfolio_risks": risk_rows[:10],
        "shared_resource_conflicts": risk_conflicts,
        "unassessed_risk_count": risk_resource.get("risk_count_unassessed", 0),
        "unassessed_resource_count": len(risk_resource.get("unassessed_resources", [])),
        "recommended_management_reviews": recommendations,
        "governance_notes": [
            "This is a decision-support brief assembled from stored workspace records; it does not approve expenditure, risk acceptance, staffing transfers or baseline changes.",
            "P1/P2 labels are screening outputs from the portfolio decision matrix, not a substitute for management judgement.",
            "Monetary exposures remain separated by currency and resource conflicts require confirmed shared resource identity.",
            "Missing evidence remains unassessed; no missing value is interpreted as zero or as a green status.",
        ],
    }
