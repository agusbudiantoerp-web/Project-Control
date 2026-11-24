"""Persistent mitigation execution tracker linked to registered project risks."""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date
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


class RiskMitigationStore:
    """Workspace-local SQLite store; actor labels are not authenticated identities."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
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

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=15)
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
        if isinstance(due_date, date):
            due = due_date.isoformat()
        else:
            try:
                due = date.fromisoformat(str(due_date).strip()).isoformat()
            except (TypeError, ValueError):
                raise ValueError("due_date must be a valid ISO date") from None
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
        with self._connect() as db:
            db.execute("""
                INSERT INTO risk_mitigations(project_id, risk_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, risk_id)
                DO UPDATE SET payload_json=excluded.payload_json
            """, (project, risk, json.dumps(row, ensure_ascii=False)))
        return row

    def list_project(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT payload_json FROM risk_mitigations WHERE project_id=? ORDER BY risk_id",
                (str(project_id).strip(),),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
