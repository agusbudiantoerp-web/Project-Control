"""Recovery plan tracking with explicit targets and recorded actual progress."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _iso_date(value: Any, field: str) -> str:
    try:
        parsed = value if isinstance(value, date) else date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a valid ISO date (YYYY-MM-DD)") from None
    return parsed.isoformat()


def _finite_nonnegative(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a non-negative finite number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a non-negative finite number") from None
    if number < 0 or number != number or number == float("inf") or number == float("-inf"):
        raise ValueError(f"{field} must be a non-negative finite number")
    return number


def create_recovery_plan(
    *, project_id: str, title: str, owner: str, start_date: Any, target_finish: Any,
    baseline_finish: Any, milestones: list[dict[str, Any]], plan_id: str | None = None,
) -> dict[str, Any]:
    """Validate and normalize a recovery plan; milestones use explicit 0-100 targets."""
    project_id, title, owner = str(project_id).strip(), str(title).strip(), str(owner).strip()
    if not project_id or not title or not owner:
        raise ValueError("project_id, title and owner are required")
    start, target, baseline = (
        _iso_date(start_date, "start_date"),
        _iso_date(target_finish, "target_finish"),
        _iso_date(baseline_finish, "baseline_finish"),
    )
    if target < start:
        raise ValueError("target_finish cannot be earlier than start_date")
    if not isinstance(milestones, list) or not milestones:
        raise ValueError("at least one milestone is required")
    normalized = []
    seen = set()
    for item in milestones:
        milestone_id = str(item.get("milestone_id") or uuid.uuid4()).strip()
        if milestone_id in seen:
            raise ValueError("milestone_id values must be unique")
        seen.add(milestone_id)
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError("each milestone requires a name")
        due = _iso_date(item.get("due_date"), "milestone due_date")
        if due < start or due > target:
            raise ValueError("milestone due_date must fall within the recovery plan dates")
        target_pct = _finite_nonnegative(item.get("target_percent"), "target_percent")
        if target_pct > 100:
            raise ValueError("target_percent cannot exceed 100")
        normalized.append({
            "milestone_id": milestone_id, "name": name, "due_date": due,
            "owner": str(item.get("owner", owner)).strip() or owner,
            "target_percent": target_pct,
            "actual_percent": 0.0, "status": "NOT_STARTED",
            "last_updated": None, "note": "",
        })
    normalized.sort(key=lambda row: (row["due_date"], row["milestone_id"]))
    return {
        "plan_id": plan_id or str(uuid.uuid4()), "project_id": project_id,
        "title": title, "owner": owner, "start_date": start,
        "target_finish": target, "baseline_finish": baseline,
        "status": "ACTIVE", "milestones": normalized,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def evaluate_recovery_plan(plan: dict[str, Any], *, as_of: Any = None) -> dict[str, Any]:
    """Summarize target attainment; overdue is based on incomplete milestone due dates."""
    review_date = _iso_date(as_of or date.today(), "as_of")
    milestones = plan.get("milestones", [])
    if not milestones:
        raise ValueError("recovery plan has no milestones")
    target_total = sum(row["target_percent"] for row in milestones)
    actual_total = sum(_finite_nonnegative(row.get("actual_percent", 0), "actual_percent") for row in milestones)
    if any(_finite_nonnegative(row.get("actual_percent", 0), "actual_percent") > 100 for row in milestones):
        raise ValueError("actual_percent cannot exceed 100")
    weighted_target = target_total / len(milestones)
    weighted_actual = actual_total / len(milestones)
    overdue = [
        row["milestone_id"] for row in milestones
        if row.get("status") != "COMPLETED" and row["due_date"] < review_date
    ]
    return {
        "plan_id": plan.get("plan_id"), "project_id": plan.get("project_id"),
        "status": "OVERDUE_MILESTONES" if overdue else "ON_TRACK_OR_NOT_DUE",
        "as_of": review_date, "milestone_count": len(milestones),
        "completed_count": sum(row.get("status") == "COMPLETED" for row in milestones),
        "overdue_count": len(overdue), "overdue_milestone_ids": overdue,
        "average_target_percent": round(weighted_target, 2),
        "average_actual_percent": round(weighted_actual, 2),
        "progress_gap_percentage_points": round(weighted_target - weighted_actual, 2),
        "milestones": milestones,
        "limitations": [
            "Progress is an unweighted average of milestone percentages; it is not earned value or physical progress.",
            "Milestone completion and actual percentages must be evidenced and approved by project controls.",
            "This tracker does not change the approved baseline or authorize acceleration costs.",
        ],
    }


class RecoveryPlanStore:
    """SQLite storage for recovery plans and append-only progress updates."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS recovery_plans (
                plan_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, payload_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS recovery_progress_events (
                event_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(plan_id) REFERENCES recovery_plans(plan_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_recovery_plans_project ON recovery_plans(project_id)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create(self, **kwargs: Any) -> dict[str, Any]:
        plan = create_recovery_plan(**kwargs)
        with self._connect() as db:
            db.execute("INSERT INTO recovery_plans(plan_id,project_id,payload_json) VALUES(?,?,?)",
                       (plan["plan_id"], plan["project_id"], json.dumps(plan)))
        return plan

    def update_milestone(self, plan_id: str, milestone_id: str, *, actual_percent: Any,
                         status: str, changed_by: str, note: str = "",
                         occurred_at: str | None = None) -> dict[str, Any]:
        actual = _finite_nonnegative(actual_percent, "actual_percent")
        if actual > 100:
            raise ValueError("actual_percent cannot exceed 100")
        status = str(status).strip().upper()
        if status not in {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED"}:
            raise ValueError("unsupported milestone status")
        if status == "COMPLETED" and actual != 100:
            raise ValueError("completed milestone must have actual_percent of 100")
        timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload_json FROM recovery_plans WHERE plan_id=?", (plan_id,)).fetchone()
            if row is None:
                raise KeyError(f"Recovery plan not found: {plan_id}")
            plan = json.loads(row["payload_json"])
            target = next((m for m in plan["milestones"] if m["milestone_id"] == milestone_id), None)
            if target is None:
                raise KeyError(f"Milestone not found: {milestone_id}")
            if actual < target["actual_percent"]:
                raise ValueError("actual_percent cannot decrease; record a reviewed correction separately")
            target.update({"actual_percent": actual, "status": status,
                           "last_updated": timestamp, "note": str(note)})
            db.execute("UPDATE recovery_plans SET payload_json=? WHERE plan_id=?",
                       (json.dumps(plan), plan_id))
            event = {"event_id": str(uuid.uuid4()), "plan_id": plan_id,
                     "milestone_id": milestone_id, "actual_percent": actual,
                     "status": status, "changed_by": str(changed_by),
                     "note": str(note), "occurred_at": timestamp}
            db.execute("INSERT INTO recovery_progress_events VALUES(?,?,?,?)",
                       (event["event_id"], plan_id, timestamp, json.dumps(event)))
            db.commit()
        return {"plan": plan, "event": event}

    def get(self, plan_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT payload_json FROM recovery_plans WHERE plan_id=?", (plan_id,)).fetchone()
            if row is None:
                raise KeyError(f"Recovery plan not found: {plan_id}")
            plan = json.loads(row["payload_json"])
            events = [json.loads(r["payload_json"]) for r in db.execute(
                "SELECT payload_json FROM recovery_progress_events WHERE plan_id=? ORDER BY rowid", (plan_id,)
            )]
        return {"plan": plan, "events": events}

    def list_project(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload_json FROM recovery_plans WHERE project_id=? ORDER BY rowid DESC",
                              (str(project_id),)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
