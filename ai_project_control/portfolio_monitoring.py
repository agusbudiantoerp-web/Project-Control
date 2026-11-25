"""Deterministic portfolio snapshot monitoring and change detection.

This is an on-demand monitoring primitive. Scheduling and delivery are delegated
to the host deployment; no background polling or external notification occurs.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


METRICS = ("SPI", "CPI", "risk_score", "delayed_activity_count", "overdue_action_count")


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def compare_portfolio_snapshots(
    previous: Iterable[dict[str, Any]],
    current: Iterable[dict[str, Any]],
    *,
    material_change: float = 0.05,
) -> dict[str, Any]:
    """Compare keyed project metrics; missing metrics remain unassessed."""
    if not 0 <= material_change <= 1:
        raise ValueError("material_change must be between 0 and 1")
    old = {str(row.get("project_id", "")).strip(): row for row in previous
           if str(row.get("project_id", "")).strip()}
    new = {str(row.get("project_id", "")).strip(): row for row in current
           if str(row.get("project_id", "")).strip()}
    changes: list[dict[str, Any]] = []
    for project_id in sorted(set(old) | set(new)):
        if project_id not in old:
            changes.append({"project_id": project_id, "metric": "PROJECT", "change": "ADDED"})
            continue
        if project_id not in new:
            changes.append({"project_id": project_id, "metric": "PROJECT", "change": "REMOVED"})
            continue
        for metric in METRICS:
            before, after = _number(old[project_id].get(metric)), _number(new[project_id].get(metric))
            if before is None or after is None:
                continue
            delta = after - before
            relative = abs(delta) / max(abs(before), 1.0)
            adverse = (
                (metric in {"SPI", "CPI"} and delta < 0)
                or (metric in {"risk_score", "delayed_activity_count", "overdue_action_count"} and delta > 0)
            )
            if adverse and relative >= material_change:
                changes.append({
                    "project_id": project_id, "metric": metric,
                    "change": "ADVERSE_INCREASE" if delta > 0 else "ADVERSE_DECREASE",
                    "previous": before, "current": after, "delta": delta,
                    "relative_change": relative,
                })
    return {
        "status": "CHANGES_DETECTED" if changes else "NO_MATERIAL_ADVERSE_CHANGE",
        "change_count": len(changes),
        "changes": changes,
        "limitations": [
            "Only adverse changes of configured relative magnitude are listed.",
            "Missing or invalid metric pairs are not compared.",
            "A snapshot comparison is not a causal diagnosis or approval to change a baseline.",
        ],
    }


class PortfolioMonitoringStore:
    """Small local SQLite history of explicitly submitted portfolio snapshots."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_monitor_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    captured_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def save_snapshot(self, projects: list[dict[str, Any]], *, captured_at: str | None = None) -> dict[str, Any]:
        if not isinstance(projects, list) or any(not isinstance(row, dict) for row in projects):
            raise TypeError("projects must be a list of dictionaries")
        ids = [str(row.get("project_id", "")).strip() for row in projects]
        if any(not item for item in ids) or len(set(ids)) != len(ids):
            raise ValueError("each project requires a unique non-empty project_id")
        timestamp = captured_at or datetime.now(timezone.utc).isoformat()
        snapshot_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute(
                "INSERT INTO portfolio_monitor_snapshots(snapshot_id,captured_at,payload_json) VALUES(?,?,?)",
                (snapshot_id, timestamp, json.dumps(projects, ensure_ascii=False, default=str)),
            )
        return {"snapshot_id": snapshot_id, "captured_at": timestamp, "project_count": len(projects)}

    def compare_with_previous(self, projects: list[dict[str, Any]], *, captured_at: str | None = None) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                "SELECT payload_json FROM portfolio_monitor_snapshots ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        previous = json.loads(row["payload_json"]) if row else []
        comparison = compare_portfolio_snapshots(previous, projects)
        saved = self.save_snapshot(projects, captured_at=captured_at)
        return {**comparison, "snapshot": saved, "previous_snapshot_available": row is not None}
