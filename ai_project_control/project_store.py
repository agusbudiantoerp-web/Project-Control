"""Local SQLite persistence for validated project-control datasets.

The store is workspace-local, uses explicit project scoping, parameterized SQL,
transactions, and an append-only import event log. It is not a multi-user or
server-grade database and must not be exposed directly to the public internet.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data_quality_validation import TABLE_KEYS, validate_project_control_data

SCHEMA_VERSION = 1


class _ClosingConnection(sqlite3.Connection):
    """Commit/rollback with the context manager, then always release the handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class ProjectStore:
    """SQLite repository for one local project-control workspace."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._sqlite_uri = False
        self._memory_keeper = None
        self._closed = False
        if self.database_path == ":memory:":
            # Each store operation opens its own connection. A shared-cache
            # URI plus a keeper connection makes the in-memory database live
            # across those operations instead of silently creating empty DBs.
            self._sqlite_target = f"file:project_control_{uuid.uuid4().hex}?mode=memory&cache=shared"
            self._sqlite_uri = True
            self._memory_keeper = sqlite3.connect(self._sqlite_target, uri=True, timeout=15)
        else:
            path = Path(self.database_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.database_path = str(path)
            self._sqlite_target = self.database_path
        try:
            self._initialise()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Release the keeper connection used by an in-memory workspace."""
        keeper = self._memory_keeper
        self._memory_keeper = None
        self._closed = True
        if keeper is not None:
            keeper.close()

    def __enter__(self) -> "ProjectStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("ProjectStore is closed")
        connection = sqlite3.connect(
            self._sqlite_target, timeout=15, uri=self._sqlite_uri,
            factory=_ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialise(self) -> None:
        with self._connect() as db:
            metadata_exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='store_metadata'"
            ).fetchone()
            if metadata_exists is not None:
                current = db.execute(
                    "SELECT value FROM store_metadata WHERE key=?",
                    ("schema_version",),
                ).fetchone()
                if current is not None:
                    try:
                        current_version = int(current["value"])
                    except (TypeError, ValueError):
                        raise RuntimeError("Workspace database schema metadata is invalid.") from None
                    if current_version > SCHEMA_VERSION:
                        raise RuntimeError(
                            "Workspace database schema is newer than this application; "
                            "upgrade the application before opening this database."
                        )
                    if current_version < SCHEMA_VERSION:
                        raise RuntimeError(
                            "Workspace database schema is older than this application; "
                            "run a supported backup and migration before opening this database."
                        )
            db.execute("""
                CREATE TABLE IF NOT EXISTS project_records (
                    project_id TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, dataset, record_key)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS import_events (
                    event_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    imported_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS store_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            db.execute(
                "INSERT OR IGNORE INTO store_metadata(key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )

    @staticmethod
    def _record_key(dataset: str, row: dict[str, Any]) -> str:
        fields = TABLE_KEYS[dataset]
        values = [str(row.get(field, "")).strip() for field in fields]
        if any(not value for value in values):
            raise ValueError(f"Missing key fields for {dataset}: {', '.join(fields)}")
        return json.dumps(values, ensure_ascii=False, separators=(",", ":"))

    def save_dataset(
        self,
        project_id: str,
        dataset: str,
        rows: list[dict[str, Any]],
        *,
        mode: str = "upsert",
    ) -> dict[str, Any]:
        """Validate and atomically upsert records belonging to project_id."""
        project_id = str(project_id).strip()
        if not project_id:
            raise ValueError("project_id is required")
        if dataset not in TABLE_KEYS:
            raise ValueError(f"Unsupported dataset: {dataset}")
        if mode not in {"upsert", "replace"}:
            raise ValueError("mode must be 'upsert' or 'replace'")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise TypeError("rows must be a list of dictionaries")

        normalized = [dict(row) for row in rows]
        for index, row in enumerate(normalized):
            row_project = str(row.get("project_id", "")).strip()
            if row_project != project_id:
                raise ValueError(
                    f"Row {index} belongs to project '{row_project}', not '{project_id}'"
                )

        # Detect repeated natural keys before schema validation so callers get
        # a stable, actionable import error rather than a validator-specific one.
        keys_seen = set()
        for row in normalized:
            key = self._record_key(dataset, row)
            if key in keys_seen and dataset != "portfolio_snapshots":
                raise ValueError(f"Duplicate record key in import: {key}")
            keys_seen.add(key)

        if dataset == "project_master":
            validation = validate_project_control_data({"project_master": normalized})
        else:
            # Validate table shape and record-local constraints. Cross-table links
            # are checked when a full workspace snapshot is requested.
            validation = validate_project_control_data({dataset: normalized})
        if validation["status"] == "INVALID":
            raise ValueError("Dataset validation failed: " + json.dumps(validation["issues"]))

        prepared = []
        seen = set()
        for index, row in enumerate(normalized):
            key = self._record_key(dataset, row)
            if key in seen:
                if dataset != "portfolio_snapshots":
                    raise ValueError(f"Duplicate record key in import: {key}")
                key = f"{key}#duplicate:{index}"
            seen.add(key)
            prepared.append((project_id, dataset, key,
                             json.dumps(row, ensure_ascii=False, default=str),
                             datetime.now(timezone.utc).isoformat()))

        event_id = str(uuid.uuid4())
        imported_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            if dataset != "project_master":
                exists = db.execute(
                    "SELECT 1 FROM project_records WHERE project_id=? AND dataset='project_master' LIMIT 1",
                    (project_id,),
                ).fetchone()
                if exists is None:
                    raise ValueError(f"Project '{project_id}' must exist in project_master first")
            if mode == "replace":
                db.execute(
                    "DELETE FROM project_records WHERE project_id=? AND dataset=?",
                    (project_id, dataset),
                )
            db.executemany("""
                INSERT INTO project_records(project_id, dataset, record_key, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, dataset, record_key)
                DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
            """, prepared)
            db.execute("""
                INSERT INTO import_events(event_id, project_id, dataset, mode, row_count,
                                          imported_at, status, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, project_id, dataset, mode, len(prepared), imported_at,
                  "COMMITTED", json.dumps({"validation_status": validation["status"]})))
        return {
            "event_id": event_id,
            "project_id": project_id,
            "dataset": dataset,
            "mode": mode,
            "saved_count": len(prepared),
            "status": "COMMITTED",
            "validation_status": validation["status"],
        }


    def save_datasets(
        self,
        project_id: str,
        datasets: dict[str, list[dict[str, Any]]],
        *,
        mode: str = "upsert",
    ) -> dict[str, dict[str, Any]]:
        """Validate and commit multiple project datasets in one SQLite transaction."""
        project_id = str(project_id).strip()
        if not project_id:
            raise ValueError("project_id is required")
        if not isinstance(datasets, dict) or not datasets:
            raise ValueError("datasets must be a non-empty mapping")
        if mode not in {"upsert", "replace"}:
            raise ValueError("mode must be 'upsert' or 'replace'")
        unknown = set(datasets) - set(TABLE_KEYS)
        if unknown:
            raise ValueError("Unsupported datasets: " + ", ".join(sorted(unknown)))

        normalized: dict[str, list[dict[str, Any]]] = {}
        prepared: dict[str, list[tuple[str, str, str, str, str]]] = {}
        validations: dict[str, str] = {}
        now = datetime.now(timezone.utc).isoformat()
        for dataset, rows in datasets.items():
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise TypeError(f"{dataset} rows must be a list of dictionaries")
            normalized[dataset] = [dict(row) for row in rows]
            seen: set[str] = set()
            dataset_prepared = []
            for index, row in enumerate(normalized[dataset]):
                row_project = str(row.get("project_id", "")).strip()
                if row_project != project_id:
                    raise ValueError(
                        f"{dataset} row {index} belongs to project '{row_project}', not '{project_id}'"
                    )
                key = self._record_key(dataset, row)
                if key in seen and dataset != "portfolio_snapshots":
                    raise ValueError(f"Duplicate record key in {dataset} import: {key}")
                if key in seen:
                    key = f"{key}#duplicate:{index}"
                seen.add(key)
                dataset_prepared.append((
                    project_id, dataset, key,
                    json.dumps(row, ensure_ascii=False, default=str), now,
                ))
            prepared[dataset] = dataset_prepared

        validation = validate_project_control_data(normalized)
        if validation["status"] == "INVALID":
            raise ValueError("Multi-dataset validation failed: " + json.dumps(validation["issues"]))
        for dataset in normalized:
            validations[dataset] = validation["status"]

        results: dict[str, dict[str, Any]] = {}
        with self._connect() as db:
            existing = db.execute(
                "SELECT 1 FROM project_records WHERE project_id=? AND dataset='project_master' LIMIT 1",
                (project_id,),
            ).fetchone()
            has_project_master = bool(normalized.get("project_master")) or existing is not None
            if any(name != "project_master" for name in normalized) and not has_project_master:
                raise ValueError(f"Project '{project_id}' must exist in project_master first")

            # Write project_master first so new-project imports can include related tables.
            ordered = sorted(normalized, key=lambda name: (name != "project_master", name))
            for dataset in ordered:
                event_id = str(uuid.uuid4())
                imported_at = datetime.now(timezone.utc).isoformat()
                if mode == "replace":
                    db.execute(
                        "DELETE FROM project_records WHERE project_id=? AND dataset=?",
                        (project_id, dataset),
                    )
                db.executemany("""
                    INSERT INTO project_records(project_id, dataset, record_key, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, dataset, record_key)
                    DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """, prepared[dataset])
                db.execute("""
                    INSERT INTO import_events(event_id, project_id, dataset, mode, row_count,
                                              imported_at, status, details_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, project_id, dataset, mode, len(prepared[dataset]),
                    imported_at, "COMMITTED",
                    json.dumps({"validation_status": validations[dataset], "atomic_batch": True}),
                ))
                results[dataset] = {
                    "event_id": event_id, "project_id": project_id,
                    "dataset": dataset, "mode": mode,
                    "saved_count": len(prepared[dataset]), "status": "COMMITTED",
                    "validation_status": validations[dataset],
                }
        return results

    def list_project_ids(self) -> list[str]:
        """List project IDs with a saved project_master record, in stable order."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT DISTINCT project_id FROM project_records "
                "WHERE dataset='project_master' ORDER BY project_id"
            ).fetchall()
        return [str(row["project_id"]) for row in rows]

    def load_dataset(self, project_id: str, dataset: str) -> list[dict[str, Any]]:
        if dataset not in TABLE_KEYS:
            raise ValueError(f"Unsupported dataset: {dataset}")
        with self._connect() as db:
            records = db.execute(
                "SELECT payload_json FROM project_records WHERE project_id=? AND dataset=? ORDER BY record_key",
                (str(project_id).strip(), dataset),
            ).fetchall()
        return [json.loads(record["payload_json"]) for record in records]

    def load_project_workspace(self, project_id: str) -> dict[str, list[dict[str, Any]]]:
        workspace = {name: self.load_dataset(project_id, name) for name in TABLE_KEYS}
        return workspace

    def validate_workspace(self, project_id: str) -> dict[str, Any]:
        return validate_project_control_data(self.load_project_workspace(project_id))

    def import_history(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connect() as db:
            rows = db.execute("""
                SELECT event_id, project_id, dataset, mode, row_count, imported_at, status, details_json
                FROM import_events WHERE project_id=? ORDER BY imported_at DESC LIMIT ?
            """, (str(project_id).strip(), limit)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json"))
            result.append(item)
        return result
