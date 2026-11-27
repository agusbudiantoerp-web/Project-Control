"""Governed schedule-change request decisions; never mutate an approved baseline."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def decide_schedule_change(
    change_request: dict[str, Any],
    decision: str,
    decided_by: str,
    rationale: str,
    *,
    decided_at: str | None = None,
) -> dict[str, Any]:
    if not isinstance(change_request, dict):
        raise TypeError("change_request must be a dictionary")
    if str(change_request.get("status", "")).upper() != "PENDING":
        raise ValueError("only a PENDING change request can receive a decision")
    normalized_decision = str(decision).strip().upper()
    if normalized_decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision must be APPROVED or REJECTED")
    reviewer = str(decided_by).strip()
    note = str(rationale).strip()
    if not reviewer:
        raise ValueError("decided_by is required")
    if not note:
        raise ValueError("decision rationale is required for auditability")
    result = deepcopy(change_request)
    result["status"] = normalized_decision
    result["decided_by"] = reviewer
    result["decided_at"] = decided_at or datetime.now(timezone.utc).isoformat()
    result["decision_rationale"] = note
    return result
