"""Persistent mitigation execution tracker linked to registered project risks."""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, timezone
from uuid import uuid4
from pathlib import Path
from typing import Any

VALID_STATUSES = {"PLANNED", "IN_PROGRESS", "IMPLEMENTED", "VERIFIED", "CANCELLED"}


def _text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _number(value: Any, field: str, *, minimum: float, maximum: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(result) or result < minimum or (maximum is not None and result > maximum):
        bound = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        raise ValueError(f"{field} must be finite and {bound}")
    return result


class _ClosingConnection(sqlite3.Connection):
    """Close SQLite handles after transaction context exit."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class RiskMitigationStore:
    """Workspace-local SQLite store; actor labels are not authenticated identities."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._memory_uri = None
        self._memory_anchor = None
        self._sqlite_uri = False
        self._closed = False
        if self.database_path == ":memory:":
            # Keep a shared-cache in-memory database alive across short-lived connections.
            self._memory_uri = f"file:risk_mitigation_{uuid4().hex}?mode=memory&cache=shared"
            self._sqlite_target = self._memory_uri
            self._sqlite_uri = True
            self._memory_anchor = sqlite3.connect(self._sqlite_target, uri=True, timeout=15)
        else:
            path = Path(self.database_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.database_path = str(path)
            self._sqlite_target = self.database_path
        try:
            with self._connect() as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS risk_mitigations (
                        project_id TEXT NOT NULL,
                        risk_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        PRIMARY KEY(project_id, risk_id)
                    )
                """)
                db.execute("CREATE INDEX IF NOT EXISTS idx_risk_mitigations_project ON risk_mitigations(project_id)")
                db.execute("""
                    CREATE TABLE IF NOT EXISTS risk_mitigation_events (
                        event_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        risk_id TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                """)
                db.execute("CREATE INDEX IF NOT EXISTS idx_risk_mitigation_events_project ON risk_mitigation_events(project_id, risk_id)")
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        anchor = self._memory_anchor
        self._memory_anchor = None
        self._closed = True
        if anchor is not None:
            anchor.close()

    def __enter__(self) -> "RiskMitigationStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("RiskMitigationStore is closed")
        db = sqlite3.connect(
            self._sqlite_target, uri=self._sqlite_uri, timeout=15,
            factory=_ClosingConnection,
        )
        db.row_factory = sqlite3.Row
        return db

    def save(
        self, *, project_id: str, risk_id: str, mitigation_action: str,
        owner: str, due_date: Any, status: str,
        residual_probability: float, residual_impact: float,
        evidence: str = "", updated_by: str,
    ) -> dict[str, Any]:
        project = _text(project_id, "project_id")
        risk = _text(risk_id, "risk_id")
        action = _text(mitigation_action, "mitigation_action")
        responsible = _text(owner, "owner")
        actor = _text(updated_by, "updated_by")
        state = str(status).strip().upper()
        if state not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        if isinstance(due_date, datetime):
            due = due_date.date().isoformat()
        elif isinstance(due_date, date):
            due = due_date.isoformat()
        else:
            try:
                due = date.fromisoformat(str(due_date).strip()).isoformat()
            except (TypeError, ValueError):
                raise ValueError("due_date must be a valid ISO date") from None
        if state == "VERIFIED" and not str(evidence or "").strip():
            raise ValueError("evidence is required when mitigation status is VERIFIED")
        probability = _number(residual_probability, "residual_probability", minimum=0, maximum=1)
        impact = _number(residual_impact, "residual_impact", minimum=0)
        row = {
            "project_id": project, "risk_id": risk,
            "mitigation_action": action, "owner": responsible,
            "due_date": due, "status": state,
            "residual_probability": probability, "residual_impact": impact,
            "residual_exposure": round(probability * impact, 4),
            "evidence": str(evidence or "").strip(),
            "updated_by": actor,
        }
        occurred_at = datetime.now(timezone.utc).isoformat()
        event = {
            "event_id": str(uuid4()), "project_id": project, "risk_id": risk,
            "event_type": "MITIGATION_UPSERTED", "occurred_at": occurred_at,
            "updated_by": actor, "status": state,
            "residual_probability": probability, "residual_impact": impact,
            "residual_exposure": row["residual_exposure"],
            "evidence": row["evidence"],
        }
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""
                INSERT INTO risk_mitigations(project_id, risk_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, risk_id)
                DO UPDATE SET payload_json=excluded.payload_json
            """, (project, risk, json.dumps(row, ensure_ascii=False)))
            db.execute("""
                INSERT INTO risk_mitigation_events(event_id, project_id, risk_id, occurred_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
            """, (event["event_id"], project, risk, occurred_at, json.dumps(event, ensure_ascii=False)))
            db.commit()
        return row

    def list_project(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT payload_json FROM risk_mitigations WHERE project_id=? ORDER BY risk_id",
                (str(project_id).strip(),),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_events(self, project_id: str, risk_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if risk_id:
                rows = db.execute(
                    "SELECT payload_json FROM risk_mitigation_events WHERE project_id=? AND risk_id=? ORDER BY occurred_at, rowid",
                    (str(project_id).strip(), str(risk_id).strip()),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT payload_json FROM risk_mitigation_events WHERE project_id=? ORDER BY occurred_at, rowid",
                    (str(project_id).strip(),),
                ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
