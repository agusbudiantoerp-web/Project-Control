"""Rule-based governance escalation from executive action records.

This module identifies overdue and blocked actions for human review. It does not
send notifications, change action status, or authorize project decisions.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable


def _as_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


def build_action_escalations(
    actions: Iterable[dict[str, Any]], *, as_of: date | str | None = None
) -> dict[str, Any]:
    """Return deterministic escalation recommendations using an explicit review date."""
    if as_of is None:
        review_date = date.today()
    elif isinstance(as_of, date):
        review_date = as_of
    else:
        parsed = _as_date(as_of)
        if parsed is None:
            raise ValueError("as_of must be a date or ISO date (YYYY-MM-DD)")
        review_date = parsed

    rows: list[dict[str, Any]] = []
    for action in actions:
        action_id = str(action.get("action_id", "")).strip()
        priority = str(action.get("priority", "")).strip().upper()
        status = str(action.get("status", "")).strip().upper()
        due = _as_date(action.get("due_date"))
        if not action_id or priority not in {"P1", "P2", "P3"}:
            continue
        if status in {"COMPLETED", "CANCELLED"}:
            continue

        overdue_days = (review_date - due).days if due is not None else None
        reason = None
        level = None
        recommended_action = None

        if status == "BLOCKED" and priority == "P1":
            reason = "P1_ACTION_BLOCKED"
            level = "PROJECT_DIRECTOR"
            recommended_action = "Review the blocker, assign an unblock owner, and record a decision."
        elif overdue_days is not None and overdue_days > 0 and priority == "P1":
            reason = "P1_ACTION_OVERDUE"
            level = "PROJECT_DIRECTOR"
            recommended_action = "Escalate immediately; confirm recovery owner and revised commitment."
        elif overdue_days is not None and overdue_days > 0:
            reason = "ACTION_OVERDUE"
            level = "PROJECT_MANAGER"
            recommended_action = "Contact the action owner and record a recovery date."
        elif due is None:
            reason = "DUE_DATE_UNASSESSED"
            level = "PROJECT_MANAGER"
            recommended_action = "Validate the due date before assessing timeliness."

        if reason:
            rows.append({
                "action_id": action_id,
                "project_id": str(action.get("project_id", "")),
                "title": str(action.get("title", "")),
                "owner": str(action.get("owner", "")),
                "priority": priority,
                "status": status,
                "due_date": due.isoformat() if due else None,
                "overdue_days": overdue_days if overdue_days is not None and overdue_days > 0 else 0,
                "reason": reason,
                "escalation_level": level,
                "recommended_action": recommended_action,
            })

    order = {"PROJECT_DIRECTOR": 0, "PROJECT_MANAGER": 1}
    rows.sort(key=lambda row: (
        order[row["escalation_level"]],
        -row["overdue_days"],
        row["action_id"],
    ))
    return {
        "status": "ESCALATIONS_PRESENT" if rows else "NO_ESCALATIONS",
        "as_of": review_date.isoformat(),
        "escalations": rows,
        "summary": {
            "escalation_count": len(rows),
            "director_count": sum(row["escalation_level"] == "PROJECT_DIRECTOR" for row in rows),
            "manager_count": sum(row["escalation_level"] == "PROJECT_MANAGER" for row in rows),
            "p1_count": sum(row["priority"] == "P1" for row in rows),
        },
        "limitations": [
            "Escalations are recommendations for human review; no notification is sent.",
            "Action owner and actor fields are not authenticated identities.",
            "Invalid or missing due dates are surfaced as unassessed, not treated as overdue.",
        ],
    }
