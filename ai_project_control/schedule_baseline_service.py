"""Immutable schedule-baseline snapshots and current-schedule variance analysis."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def _activity_index(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise TypeError(f"{label} must be a list of activity dictionaries")
    indexed: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        activity_id = str(row.get("activity_id", "")).strip()
        if not activity_id:
            raise ValueError(f"{label} row {index} is missing activity_id")
        if activity_id in indexed:
            raise ValueError(f"{label} contains duplicate activity_id: {activity_id}")
        indexed[activity_id] = deepcopy(row)
    return indexed


def create_schedule_baseline(
    project_id: str,
    baseline_id: str,
    activities: list[dict[str, Any]],
    *,
    baseline_name: str = "",
    created_by: str = "",
    version: int = 1,
) -> dict[str, Any]:
    """Capture a draft snapshot. Later edits to source rows cannot mutate it."""
    project_id = str(project_id).strip()
    baseline_id = str(baseline_id).strip()
    if not project_id or not baseline_id:
        raise ValueError("project_id and baseline_id are required")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("version must be a positive integer")
    snapshot = _activity_index(activities, "activities")
    if not snapshot:
        raise ValueError("cannot create a schedule baseline without activities")
    return {
        "project_id": project_id,
        "baseline_id": baseline_id,
        "baseline_name": str(baseline_name).strip() or baseline_id,
        "version": version,
        "status": "DRAFT",
        "created_by": str(created_by).strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approved_by": "",
        "approved_at": "",
        "activity_count": len(snapshot),
        "activities_snapshot": list(snapshot.values()),
    }


def approve_schedule_baseline(
    baseline: dict[str, Any],
    approved_by: str,
    *,
    approved_at: str | None = None,
) -> dict[str, Any]:
    """Approve a draft snapshot; approved baselines cannot be re-approved."""
    if not isinstance(baseline, dict):
        raise TypeError("baseline must be a dictionary")
    if baseline.get("status") != "DRAFT":
        raise ValueError("only a DRAFT baseline can be approved")
    approver = str(approved_by).strip()
    if not approver:
        raise ValueError("approved_by is required")
    approved = deepcopy(baseline)
    approved["status"] = "APPROVED"
    approved["approved_by"] = approver
    approved["approved_at"] = approved_at or datetime.now(timezone.utc).isoformat()
    return approved


def compare_schedule_to_baseline(
    baseline: dict[str, Any],
    current_activities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Report activity additions, removals and key date/duration variances."""
    if not isinstance(baseline, dict):
        raise TypeError("baseline must be a dictionary")
    baseline_rows = _activity_index(
        baseline.get("activities_snapshot", []), "baseline activities_snapshot"
    )
    current_rows = _activity_index(current_activities, "current_activities")
    added = sorted(set(current_rows) - set(baseline_rows))
    removed = sorted(set(baseline_rows) - set(current_rows))
    fields = ("wbs_id", "planned_start", "planned_finish", "duration_days",
              "predecessor_ids", "predecessors")
    changed = []
    for activity_id in sorted(set(current_rows) & set(baseline_rows)):
        before, after = baseline_rows[activity_id], current_rows[activity_id]
        differences = {
            field: {"baseline": before.get(field), "current": after.get(field)}
            for field in fields if before.get(field) != after.get(field)
        }
        if differences:
            changed.append({"activity_id": activity_id, "differences": differences})
    return {
        "project_id": baseline.get("project_id"),
        "baseline_id": baseline.get("baseline_id"),
        "baseline_status": baseline.get("status", "UNKNOWN"),
        "baseline_activity_count": len(baseline_rows),
        "current_activity_count": len(current_rows),
        "added_activity_ids": added,
        "removed_activity_ids": removed,
        "changed_activities": changed,
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "status": "UNCHANGED" if not (added or removed or changed) else "VARIANCE_DETECTED",
        "limitations": [
            "This is a schedule data comparison, not a contractual change approval.",
            "Date strings are compared as supplied; normalize calendars and time zones before analysis.",
        ],
    }
