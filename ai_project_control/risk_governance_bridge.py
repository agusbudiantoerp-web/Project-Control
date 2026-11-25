"""Join risk register, executive actions and mitigation execution for governance review."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def build_risk_governance_view(
    risks: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    mitigations: list[dict[str, Any]],
    *,
    as_of_date: date | str | None = None,
) -> dict[str, Any]:
    if any(not isinstance(rows, list) for rows in (risks, actions, mitigations)):
        raise TypeError("risks, actions and mitigations must be lists of dictionaries")
    if any(not isinstance(row, dict) for rows in (risks, actions, mitigations) for row in rows):
        raise TypeError("all records must be dictionaries")
    if as_of_date is None:
        cutoff = date.today()
    elif isinstance(as_of_date, datetime):
        cutoff = as_of_date.date()
    elif isinstance(as_of_date, date):
        cutoff = as_of_date
    else:
        try:
            cutoff = date.fromisoformat(str(as_of_date))
        except ValueError:
            raise ValueError("as_of_date must be a valid ISO date") from None

    risk_ids = [str(row.get("risk_id", "")).strip() for row in risks]
    if any(not value for value in risk_ids) or len(risk_ids) != len(set(risk_ids)):
        raise ValueError("risk register must contain unique, non-empty risk_id values")

    action_map: dict[str, list[dict[str, Any]]] = {}
    for action in actions:
        risk_id = str(action.get("risk_id") or "").strip()
        if risk_id:
            action_map.setdefault(risk_id, []).append(action)
    mitigation_map = {
        str(row.get("risk_id", "")).strip(): row
        for row in mitigations if str(row.get("risk_id", "")).strip()
    }

    rows = []
    for risk in risks:
        risk_id = str(risk["risk_id"]).strip()
        linked_actions = action_map.get(risk_id, [])
        mitigation = mitigation_map.get(risk_id)
        active = [row for row in linked_actions if str(row.get("status", "")).upper() not in {"COMPLETED", "CANCELLED"}]
        overdue = []
        for action in active:
            try:
                due = date.fromisoformat(str(action.get("due_date", "")))
            except ValueError:
                continue
            if due < cutoff:
                overdue.append(action)
        rows.append({
            "risk_id": risk_id,
            "risk_description": str(risk.get("description", risk.get("risk_description", ""))),
            "risk_owner": str(risk.get("risk_owner", risk.get("owner", ""))),
            "priority": str(risk.get("priority", "")),
            "linked_action_count": len(linked_actions),
            "active_action_count": len(active),
            "blocked_action_count": sum(str(row.get("status", "")).upper() == "BLOCKED" for row in active),
            "overdue_action_count": len(overdue),
            "mitigation_status": mitigation.get("status", "NOT_PLANNED") if mitigation else "NOT_PLANNED",
            "mitigation_owner": mitigation.get("owner", "") if mitigation else "",
            "mitigation_due_date": mitigation.get("due_date", "") if mitigation else "",
            "residual_exposure": mitigation.get("residual_exposure") if mitigation else None,
            "mitigation_evidence_present": bool(str(mitigation.get("evidence", "")).strip()) if mitigation else False,
            "governance_attention": bool(overdue or any(str(row.get("status", "")).upper() == "BLOCKED" for row in active) or not mitigation),
        })

    known = set(risk_ids)
    orphan_action_count = sum(
        bool(str(row.get("risk_id") or "").strip())
        and str(row.get("risk_id")).strip() not in known
        for row in actions
    )
    orphan_mitigation_count = sum(
        str(row.get("risk_id", "")).strip() not in known
        for row in mitigations
    )
    return {
        "status": "ASSESSED" if rows else "NO_RISKS",
        "as_of_date": cutoff.isoformat(),
        "risk_count": len(rows),
        "risks_requiring_attention": sum(row["governance_attention"] for row in rows),
        "overdue_action_count": sum(row["overdue_action_count"] for row in rows),
        "blocked_action_count": sum(row["blocked_action_count"] for row in rows),
        "risks_without_mitigation": sum(row["mitigation_status"] == "NOT_PLANNED" for row in rows),
        "orphan_action_count": orphan_action_count,
        "orphan_mitigation_count": orphan_mitigation_count,
        "rows": rows,
        "limitations": [
            "Only actions explicitly linked by risk_id are counted; no relationship is inferred.",
            "Mitigation completion and evidence are reported, not independently verified.",
            "Residual exposure is only comparable when all risk impacts use the same unit and currency.",
            "This view is a governance worklist, not an automated risk acceptance decision.",
        ],
    }
