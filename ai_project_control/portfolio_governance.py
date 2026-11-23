"""Role-gated recovery governance workflow with append-only decision history."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid
from typing import Any

import pandas as pd

COLUMNS = [
    "request_id", "project_id", "scenario", "recovery_action", "owner",
    "requested_by", "proposed_budget", "currency", "status", "created_at",
    "pm_approved_by", "pm_approved_at", "director_approved_by", "director_approved_at",
    "coo_approved_by", "coo_approved_at", "rejection_reason", "started_at", "closed_at",
    "decision_history",
]

TRANSITIONS = {
    "Proposed": {"PM Approved", "Rejected"},
    "PM Approved": {"Director Approved", "Rejected"},
    "Director Approved": {"COO Approved", "Rejected"},
    "COO Approved": {"In Progress", "Rejected"},
    "In Progress": {"Closed", "Rejected"},
    "Rejected": set(),
    "Closed": set(),
}

ROLE_FOR_STATUS = {
    "PM Approved": "Project Manager",
    "Director Approved": "Project Director",
    "COO Approved": "COO",
    "In Progress": "Project Manager",
    "Closed": "Project Manager",
    "Rejected": "Project Manager",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _history(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return []
    return []


def submit_recovery_action(
    register: pd.DataFrame | None,
    *,
    project_id: str,
    scenario: str,
    recovery_action: str,
    owner: str,
    requested_by: str,
    proposed_budget: float,
    currency: str,
) -> dict[str, Any]:
    """Create a proposed recovery action; it is never auto-approved."""
    current = register.copy() if isinstance(register, pd.DataFrame) else pd.DataFrame(columns=COLUMNS)
    if current.empty:
        current = pd.DataFrame(columns=COLUMNS)
    required = {
        "project_id": project_id, "scenario": scenario, "recovery_action": recovery_action,
        "owner": owner, "requested_by": requested_by, "currency": currency,
    }
    missing = [key for key, value in required.items() if not str(value).strip()]
    if missing:
        raise ValueError("Required fields missing: " + ", ".join(missing))
    try:
        budget = float(proposed_budget)
    except (TypeError, ValueError):
        raise ValueError("Proposed budget must be numeric.")
    if not pd.notna(budget) or budget < 0:
        raise ValueError("Proposed budget must be finite and non-negative.")
    if not pd.isna(budget) and budget == float("inf"):
        raise ValueError("Proposed budget must be finite and non-negative.")
    request_id = "REC-" + uuid.uuid4().hex[:10].upper()
    now = _now()
    event = {"timestamp": now, "from": None, "to": "Proposed",
             "actor": str(requested_by).strip(), "role": "Requester", "note": "Submitted for review"}
    row = {
        "request_id": request_id, "project_id": str(project_id).strip(),
        "scenario": str(scenario).strip(), "recovery_action": str(recovery_action).strip(),
        "owner": str(owner).strip(), "requested_by": str(requested_by).strip(),
        "proposed_budget": budget, "currency": str(currency).strip().upper(),
        "status": "Proposed", "created_at": now,
        "pm_approved_by": None, "pm_approved_at": None,
        "director_approved_by": None, "director_approved_at": None,
        "coo_approved_by": None, "coo_approved_at": None,
        "rejection_reason": None, "started_at": None, "closed_at": None,
        "decision_history": json.dumps([event], ensure_ascii=False),
    }
    updated = pd.concat([current, pd.DataFrame([row])], ignore_index=True)
    return {"register": updated.reindex(columns=COLUMNS), "request_id": request_id}


def transition_recovery_action(
    register: pd.DataFrame,
    request_id: str,
    target_status: str,
    actor: str,
    role: str,
    note: str = "",
) -> pd.DataFrame:
    """Apply one permitted transition and append an audit event."""
    if not isinstance(register, pd.DataFrame) or register.empty:
        raise ValueError("No recovery governance register exists.")
    if not str(actor).strip():
        raise ValueError("Actor name is required.")
    if request_id not in register["request_id"].astype(str).values:
        raise ValueError("Recovery request was not found.")
    if target_status not in ROLE_FOR_STATUS:
        raise ValueError("Unsupported target status.")
    updated = register.copy(deep=True)
    idx = updated.index[updated["request_id"].astype(str) == str(request_id)][0]
    row = updated.loc[idx]
    current = str(row["status"])
    if target_status not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Transition {current} -> {target_status} is not permitted.")
    if target_status == "Rejected":
        expected_role = {
            "Proposed": "Project Manager",
            "PM Approved": "Project Director",
            "Director Approved": "COO",
            "COO Approved": "COO",
            "In Progress": "Project Manager",
        }.get(current)
    else:
        expected_role = ROLE_FOR_STATUS[target_status]
    if str(role).strip() != expected_role:
        raise PermissionError(f"{target_status} from {current} requires role: {expected_role}.")
    if target_status == "Rejected" and not str(note).strip():
        raise ValueError("A rejection reason is required.")
    if target_status == "Closed" and not str(note).strip():
        raise ValueError("Closure evidence or completion note is required.")
    now = _now()
    updated.at[idx, "status"] = target_status
    updated.at[idx, "decision_history"] = json.dumps(
        _history(row.get("decision_history")) + [{
            "timestamp": now, "from": current, "to": target_status,
            "actor": str(actor).strip(), "role": str(role).strip(),
            "note": str(note).strip(),
        }], ensure_ascii=False,
    )
    fields = {
        "PM Approved": ("pm_approved_by", "pm_approved_at"),
        "Director Approved": ("director_approved_by", "director_approved_at"),
        "COO Approved": ("coo_approved_by", "coo_approved_at"),
        "In Progress": ("started_at",),
        "Closed": ("closed_at",),
        "Rejected": ("rejection_reason",),
    }
    for field in fields.get(target_status, ()):
        updated.at[idx, field] = str(note).strip() if field == "rejection_reason" else (
            str(actor).strip() if field.endswith("_by") else now
        )
    return updated


def governance_summary(register: pd.DataFrame | None) -> dict[str, int]:
    if not isinstance(register, pd.DataFrame) or register.empty or "status" not in register:
        return {status: 0 for status in TRANSITIONS}
    counts = register["status"].value_counts()
    return {status: int(counts.get(status, 0)) for status in TRANSITIONS}
