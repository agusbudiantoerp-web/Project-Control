"""Consistent SQLite workspace backup using SQLite's online backup API."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

MAX_WORKSPACE_BACKUP_BYTES = 200 * 1024 * 1024


def build_workspace_backup(database_path: str | Path) -> bytes:
    """Return a consistent SQLite database snapshot without modifying its source."""
    source_path = str(database_path)
    if source_path == ":memory:":
        raise ValueError("In-memory workspaces cannot be backed up by path; use a file-backed database.")
    path = Path(source_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Workspace database not found: {path}")
    with TemporaryDirectory(prefix="project-control-backup-") as temp_dir:
        target_path = Path(temp_dir) / "workspace_backup.sqlite3"
        source = sqlite3.connect(str(path), timeout=15)
        target = sqlite3.connect(str(target_path))
        try:
            source.backup(target)
            target.commit()
            integrity = target.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("Generated workspace backup failed SQLite integrity_check.")
        finally:
            target.close()
            source.close()
        if target_path.stat().st_size > MAX_WORKSPACE_BACKUP_BYTES:
            raise ValueError("Workspace backup exceeds the 200 MB backup limit.")
        data = target_path.read_bytes()
    if not data.startswith(b"SQLite format 3\x00"):
        raise ValueError("Generated backup is not a valid SQLite database file.")
    return data
