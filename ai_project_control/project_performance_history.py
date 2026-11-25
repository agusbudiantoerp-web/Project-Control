"""Append-only project KPI history and leakage-aware next-snapshot dataset builder.

The module stores manually/externally supplied observations. It does not invent
historical values, train a model, or claim forecasts are calibrated.
"""
from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

METRICS = (
    "SPI", "CPI", "risk_score", "delayed_activity_count",
    "overdue_action_count", "planned_value", "earned_value",
    "actual_cost", "remaining_work_units", "daily_productivity",
)


def _normalise_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise TypeError("each snapshot must be a dictionary")
    project_id = str(row.get("project_id", "")).strip()
    if not project_id:
        raise ValueError("project_id is required")
    raw_date = row.get("reporting_date", row.get("date"))
    try:
        reporting_date = date.fromisoformat(str(raw_date)[:10]).isoformat()
    except (TypeError, ValueError):
        raise ValueError("reporting_date must use YYYY-MM-DD") from None
    currency = str(row.get("currency", "")).strip().upper() or None
    result: dict[str, Any] = {
        "project_id": project_id,
        "reporting_date": reporting_date,
        "currency": currency,
    }
    for metric in METRICS:
        value = row.get(metric)
        if value in (None, ""):
            result[metric] = None
            continue
        if isinstance(value, bool):
            raise ValueError(f"{metric} must be a finite non-negative number")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{metric} must be numeric") from None
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"{metric} must be a finite non-negative number")
        result[metric] = number
    if all(result[name] is None for name in METRICS):
        raise ValueError("at least one KPI metric must be provided")
    return result


class ProjectPerformanceHistoryStore:
    """SQLite store with one immutable observation per project/reporting date."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS project_performance_history (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    reporting_date TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(project_id, reporting_date)
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_history_date
                ON project_performance_history(project_id, reporting_date)
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def save(self, snapshot: dict[str, Any], *, captured_at: str | None = None) -> dict[str, Any]:
        normalised = _normalise_snapshot(snapshot)
        timestamp = captured_at or datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO project_performance_history(project_id,reporting_date,captured_at,payload_json) VALUES(?,?,?,?)",
                    (normalised["project_id"], normalised["reporting_date"], timestamp,
                     json.dumps(normalised, ensure_ascii=False, sort_keys=True)),
                )
            except sqlite3.IntegrityError:
                raise ValueError(
                    f"snapshot already exists for {normalised['project_id']} on {normalised['reporting_date']}"
                ) from None
        return {"snapshot_id": cursor.lastrowid, "captured_at": timestamp, **normalised}

    def save_many(self, snapshots: Iterable[dict[str, Any]]) -> dict[str, Any]:
        saved = []
        for snapshot in snapshots:
            saved.append(self.save(snapshot))
        return {"saved_count": len(saved), "snapshots": saved}

    def list_snapshots(self, *, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT snapshot_id,captured_at,payload_json FROM project_performance_history"
        params: tuple[Any, ...] = ()
        if project_id is not None:
            query += " WHERE project_id=?"
            params = (str(project_id).strip(),)
        query += " ORDER BY project_id, reporting_date, snapshot_id"
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        return [
            {"snapshot_id": row["snapshot_id"], "captured_at": row["captured_at"],
             **json.loads(row["payload_json"])}
            for row in rows
        ]

    def build_next_snapshot_dataset(self, *, minimum_gap_days: int = 1) -> dict[str, Any]:
        if isinstance(minimum_gap_days, bool) or not isinstance(minimum_gap_days, int) or minimum_gap_days < 1:
            raise ValueError("minimum_gap_days must be a positive integer")
        history = self.list_snapshots()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in history:
            grouped.setdefault(row["project_id"], []).append(row)
        dataset = []
        skipped_currency = 0
        for project_id, rows in grouped.items():
            for current, following in zip(rows, rows[1:]):
                gap = (date.fromisoformat(following["reporting_date"]) -
                       date.fromisoformat(current["reporting_date"])).days
                if gap < minimum_gap_days:
                    continue
                if current.get("currency") != following.get("currency"):
                    skipped_currency += 1
                    continue
                item: dict[str, Any] = {
                    "project_id": project_id,
                    "feature_date": current["reporting_date"],
                    "target_date": following["reporting_date"],
                    "gap_days": gap,
                    "currency": current.get("currency"),
                }
                for metric in METRICS:
                    item[f"feature_{metric}"] = current.get(metric)
                    item[f"target_{metric}"] = following.get(metric)
                for metric in ("SPI", "CPI", "risk_score", "delayed_activity_count",
                               "overdue_action_count", "actual_cost"):
                    before, after = current.get(metric), following.get(metric)
                    item[f"delta_{metric}"] = (
                        round(after - before, 8) if before is not None and after is not None else None
                    )
                dataset.append(item)
        return {
            "status": "READY" if dataset else "INSUFFICIENT_HISTORY",
            "row_count": len(dataset),
            "project_count": len({row["project_id"] for row in dataset}),
            "skipped_currency_mismatch_pairs": skipped_currency,
            "target_definition": "Each row uses snapshot t as features and the next chronological snapshot of the same project as target.",
            "rows": dataset,
            "limitations": [
                "Adjacent-snapshot pairs are not independent; split train/validation by project and time to reduce leakage.",
                "No model is trained by this module. Validate sample size, missingness, drift and target definitions first.",
                "Pairs with currency changes are excluded; monetary targets must not be pooled across currencies.",
                "Historical data quality and reporting consistency determine dataset usefulness.",
            ],
        }

    def export_dataset_csv(self, *, minimum_gap_days: int = 1) -> str:
        result = self.build_next_snapshot_dataset(minimum_gap_days=minimum_gap_days)
        rows = result["rows"]
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
