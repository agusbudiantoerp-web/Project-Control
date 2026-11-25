"""Durable SQLite persistence for the executive action register.

This store is workspace-local. Actor fields are attribution only; authentication,
authorization, and multi-user deployment controls belong to the host application.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .executive_action_register import (
    build_action_register, create_action, transition_action,
)


class _ClosingConnection(sqlite3.Connection):
    """Close SQLite handles after transaction context exit."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class ActionRegisterStore:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._sqlite_uri = False
        self._memory_anchor = None
        self._closed = False
        if self.database_path == ":memory:":
            self._sqlite_target = f"file:action_register_{uuid.uuid4().hex}?mode=memory&cache=shared"
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
                    CREATE TABLE IF NOT EXISTS executive_actions (
                        action_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                """)
                db.execute("""
                    CREATE TABLE IF NOT EXISTS executive_action_events (
                        event_id TEXT PRIMARY KEY,
                        action_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        FOREIGN KEY(action_id) REFERENCES executive_actions(action_id)
                    )
                """)
                db.execute("CREATE INDEX IF NOT EXISTS idx_exec_actions_project ON executive_actions(project_id)")
                db.execute("CREATE INDEX IF NOT EXISTS idx_exec_events_action ON executive_action_events(action_id)")
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        anchor = self._memory_anchor
        self._memory_anchor = None
        self._closed = True
        if anchor is not None:
            anchor.close()

    def __enter__(self) -> "ActionRegisterStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("ActionRegisterStore is closed")
        db = sqlite3.connect(
            self._sqlite_target, timeout=15, isolation_level=None,
            uri=self._sqlite_uri, factory=_ClosingConnection,
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def create(self, *, title: str, owner: str, due_date: Any, project_id: str,
               created_by: str, priority: str = "P2", description: str = "",
               action_id: str | None = None, risk_id: str | None = None) -> dict[str, Any]:
        action = create_action(
            title=title, owner=owner, due_date=due_date, project_id=project_id,
            created_by=created_by, priority=priority, description=description,
            action_id=action_id, risk_id=risk_id,
        )
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO executive_actions(action_id, project_id, payload_json) VALUES (?, ?, ?)",
                (action["action_id"], action["project_id"], json.dumps(action, ensure_ascii=False)),
            )
            db.commit()
        return action

    def transition(self, action_id: str, *, new_status: str, changed_by: str,
                   note: str = "", occurred_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload_json FROM executive_actions WHERE action_id=?", (str(action_id),)
            ).fetchone()
            if row is None:
                db.rollback()
                raise KeyError(f"Action not found: {action_id}")
            current = json.loads(row["payload_json"])
            updated, event = transition_action(
                current, new_status=new_status, changed_by=changed_by,
                note=note, occurred_at=occurred_at,
            )
            db.execute(
                "UPDATE executive_actions SET payload_json=? WHERE action_id=?",
                (json.dumps(updated, ensure_ascii=False), str(action_id)),
            )
            db.execute(
                "INSERT INTO executive_action_events(event_id, action_id, project_id, payload_json) VALUES (?, ?, ?, ?)",
                (event["event_id"], action_id, updated["project_id"],
                 json.dumps(event, ensure_ascii=False)),
            )
            db.commit()
        return updated, event

    def list_project(self, project_id: str) -> dict[str, Any]:
        with self._connect() as db:
            actions = [
                json.loads(row["payload_json"])
                for row in db.execute(
                    "SELECT payload_json FROM executive_actions WHERE project_id=?",
                    (str(project_id).strip(),),
                ).fetchall()
            ]
            events = [
                json.loads(row["payload_json"])
                for row in db.execute(
                    "SELECT payload_json FROM executive_action_events WHERE project_id=? ORDER BY rowid",
                    (str(project_id).strip(),),
                ).fetchall()
            ]
        return build_action_register(actions, events)

    def list_portfolio(self) -> dict[str, Any]:
        with self._connect() as db:
            actions = [json.loads(row["payload_json"]) for row in db.execute(
                "SELECT payload_json FROM executive_actions"
            ).fetchall()]
            events = [json.loads(row["payload_json"]) for row in db.execute(
                "SELECT payload_json FROM executive_action_events ORDER BY rowid"
            ).fetchall()]
        return build_action_register(actions, events)
