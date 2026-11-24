"""Validated executive action register with explicit, append-only event history.

This module is an in-memory domain layer. Persistence and user authentication must be
provided by the host application; it does not pretend to provide either.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

VALID_PRIORITIES = {"P1", "P2", "P3"}
VALID_STATUSES = {"OPEN", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"}
ALLOWED_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "BLOCKED", "CANCELLED"},
    "IN_PROGRESS": {"BLOCKED", "COMPLETED", "CANCELLED"},
    "BLOCKED": {"IN_PROGRESS", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


def _required_text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _date(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except (TypeError, ValueError):
        raise ValueError("due_date must be a valid ISO date (YYYY-MM-DD)") from None


def create_action(
    *, title: str, owner: str, due_date: Any, project_id: str,
    priority: str = "P2", description: str = "", created_by: str,
    action_id: str | None = None, risk_id: str | None = None,
) -> dict[str, Any]:
    """Create a validated action; created_by is attribution, not authentication."""
    priority = str(priority).strip().upper()
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(VALID_PRIORITIES)}")
    now = datetime.now(timezone.utc).isoformat()
    action = {
        "action_id": str(action_id or uuid4()),
        "title": _required_text(title, "title"),
        "owner": _required_text(owner, "owner"),
        "due_date": _date(due_date),
        "project_id": _required_text(project_id, "project_id"),
        "risk_id": str(risk_id or "").strip() or None,
        "priority": priority,
        "description": str(description or "").strip(),
        "status": "OPEN",
        "created_by": _required_text(created_by, "created_by"),
        "created_at": now,
        "updated_at": now,
    }
    return action


def transition_action(
    action: dict[str, Any], *, new_status: str, changed_by: str,
    note: str = "", occurred_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return updated action plus event; original input is never mutated."""
    current = str(action.get("status", "")).upper()
    target = str(new_status).strip().upper()
    if current not in VALID_STATUSES:
        raise ValueError("action has an invalid current status")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"transition {current} -> {target} is not allowed")
    actor = _required_text(changed_by, "changed_by")
    updated = deepcopy(action)
    timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
    updated["status"] = target
    updated["updated_at"] = timestamp
    event = {
        "event_id": str(uuid4()),
        "action_id": _required_text(action.get("action_id"), "action_id"),
        "event_type": "STATUS_CHANGED",
        "from_status": current,
        "to_status": target,
        "changed_by": actor,
        "note": str(note or "").strip(),
        "occurred_at": timestamp,
    }
    return updated, event


def build_action_register(
    actions: Iterable[dict[str, Any]], events: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build a stable register summary without altering supplied records."""
    rows = [deepcopy(item) for item in actions]
    event_rows = [deepcopy(item) for item in events]
    ids = [str(row.get("action_id", "")) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("action_id values must be unique")
    rows.sort(key=lambda row: (
        {"P1": 0, "P2": 1, "P3": 2}.get(str(row.get("priority", "")).upper(), 3),
        str(row.get("due_date", "")),
        str(row.get("action_id", "")),
    ))
    counts = {status: sum(str(row.get("status", "")).upper() == status for row in rows)
              for status in sorted(VALID_STATUSES)}
    return {
        "actions": rows,
        "events": event_rows,
        "summary": {
            "action_count": len(rows),
            "open_count": counts["OPEN"],
            "in_progress_count": counts["IN_PROGRESS"],
            "blocked_count": counts["BLOCKED"],
            "completed_count": counts["COMPLETED"],
            "cancelled_count": counts["CANCELLED"],
            "overdue_count": sum(
                str(row.get("due_date", "")) < date.today().isoformat()
                and str(row.get("status", "")).upper() not in {"COMPLETED", "CANCELLED"}
                for row in rows
            ),
        },
        "limitations": [
            "This register is a domain layer and does not persist records.",
            "created_by and changed_by are attribution fields, not authenticated identities.",
            "The host application must enforce authorization and durable audit-log storage.",
        ],
    }
