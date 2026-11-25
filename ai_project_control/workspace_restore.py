"""Validated, atomic restore for the primary local SQLite workspace."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project_store import SCHEMA_VERSION
from .workspace_backup import MAX_WORKSPACE_BACKUP_BYTES, build_workspace_backup

REQUIRED_TABLES = {"project_records", "import_events", "store_metadata"}


def _validate_backup_file(path: Path) -> dict[str, int]:
    """Validate SQLite integrity, expected schema and record counts."""
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=15)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("Workspace backup failed SQLite integrity_check.")
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if not REQUIRED_TABLES.issubset(tables):
                raise ValueError("File is not a complete Project Control workspace backup.")
            metadata = connection.execute(
                "SELECT value FROM store_metadata WHERE key='schema_version'"
            ).fetchone()
            if metadata is None:
                raise ValueError("Workspace backup has no schema version metadata.")
            try:
                version = int(metadata[0])
            except (TypeError, ValueError):
                raise ValueError("Workspace backup schema metadata is invalid.") from None
            if version != SCHEMA_VERSION:
                raise ValueError(
                    f"Workspace backup schema version {version} is not supported by this application (expected {SCHEMA_VERSION})."
                )
            project_count = connection.execute(
                "SELECT COUNT(DISTINCT project_id) FROM project_records"
            ).fetchone()[0]
            record_count = connection.execute(
                "SELECT COUNT(*) FROM project_records"
            ).fetchone()[0]
            return {"project_count": int(project_count), "record_count": int(record_count)}
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        raise ValueError("Uploaded file is not a readable SQLite workspace backup.") from None


def validate_workspace_backup(raw: bytes) -> dict[str, int]:
    """Validate uploaded backup bytes without changing the current workspace."""
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError("Workspace backup upload is empty.")
    if len(raw) > MAX_WORKSPACE_BACKUP_BYTES:
        raise ValueError("Workspace backup exceeds the 200 MB restore limit.")
    if not bytes(raw).startswith(b"SQLite format 3\x00"):
        raise ValueError("Uploaded file is not a SQLite database backup.")
    with tempfile.TemporaryDirectory(prefix="project-control-restore-check-") as temp_dir:
        candidate = Path(temp_dir) / "candidate.sqlite3"
        candidate.write_bytes(bytes(raw))
        return _validate_backup_file(candidate)


def restore_workspace_backup(
    database_path: str | Path,
    raw: bytes,
) -> dict[str, Any]:
    """Validate first, create a safety snapshot, then atomically replace the DB."""
    details = validate_workspace_backup(raw)
    if str(database_path) == ":memory:":
        raise ValueError("In-memory workspaces cannot be restored by path.")
    path = Path(database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refusing to replace a symlinked workspace database.")

    with tempfile.TemporaryDirectory(prefix="project-control-restore-") as temp_dir:
        temp_path = Path(temp_dir) / "candidate.sqlite3"
        temp_path.write_bytes(bytes(raw))
        _validate_backup_file(temp_path)

        safety_path: Path | None = None
        if path.exists():
            if not path.is_file():
                raise ValueError("Workspace database path is not a regular file.")
            safety_bytes = build_workspace_backup(path)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            safety_path = path.with_name(f"{path.name}.pre-restore-{stamp}.sqlite3")
            suffix = 1
            while safety_path.exists():
                safety_path = path.with_name(
                    f"{path.name}.pre-restore-{stamp}-{suffix}.sqlite3"
                )
                suffix += 1
            with safety_path.open("xb") as handle:
                handle.write(safety_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            if os.name != "nt":
                os.chmod(safety_path, 0o600)

        destination_temp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=f".{path.name}.restore-",
                suffix=".tmp", dir=path.parent, delete=False,
            ) as handle:
                destination_temp = Path(handle.name)
                with temp_path.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            _validate_backup_file(destination_temp)
            # Restore must be performed while no other process is writing to
            # the local SQLite workspace.
            for sidecar in (Path(str(path) + "-wal"), Path(str(path) + "-shm")):
                if sidecar.exists():
                    sidecar.unlink()
            os.replace(destination_temp, path)
            destination_temp = None
        finally:
            if destination_temp is not None:
                try:
                    destination_temp.unlink()
                except FileNotFoundError:
                    pass

    return {
        **details,
        "database_path": str(path),
        "safety_backup_path": str(safety_path) if safety_path else None,
        "status": "RESTORED",
    }
