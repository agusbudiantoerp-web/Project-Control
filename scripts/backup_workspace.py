"""Create a verified, timestamped backup of the primary local workspace.

Run from any working directory with:
    py -3.11 scripts/backup_workspace.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import os
import re
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_project_control.workspace_backup import build_workspace_backup
from ai_project_control.workspace_config import get_workspace_database_path


def create_backup(destination: Path, retention_days: int) -> Path:
    if isinstance(retention_days, bool) or not isinstance(retention_days, int) or retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    database = Path(get_workspace_database_path()).expanduser()
    if not database.is_absolute():
        database = ROOT / database
    database = database.resolve()
    if not database.is_file():
        raise FileNotFoundError(
            f"Workspace database not found: {database}. Open the application and save a project first."
        )

    destination = destination.expanduser()
    if not destination.is_absolute():
        destination = ROOT / destination
    destination = destination.resolve()
    if destination == database:
        raise ValueError("Backup destination cannot be the workspace database or a folder containing it.")
    destination.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        destination.chmod(0o700)

    payload = build_workspace_backup(database)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = destination / f"ai_project_control_{timestamp}.sqlite3"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".workspace-backup-", suffix=".tmp",
            dir=destination, delete=False,
        ) as temporary:
            temp_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        if temp_path.stat().st_size != len(payload) or not temp_path.read_bytes().startswith(b"SQLite format 3\x00"):
            raise ValueError("Backup file verification failed before publication.")
        if os.name != "nt":
            temp_path.chmod(0o600)
        os.replace(temp_path, target)
        temp_path = None
        if os.name != "nt":
            target.chmod(0o600)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for old in destination.glob("ai_project_control_*.sqlite3"):
        if old == target or not old.is_file() or not re.fullmatch(r"ai_project_control_\d{8}T\d{12}Z\.sqlite3", old.name):
            continue
        modified = datetime.fromtimestamp(old.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            old.unlink()
            removed += 1

    print(f"Backup created: {target}")
    print(f"Backup size: {target.stat().st_size:,} bytes")
    print(f"Retention: {retention_days} days; old backups removed: {removed}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe local AI Project Control SQLite backup.")
    parser.add_argument("--destination", default=".project_control/backups")
    parser.add_argument("--retention-days", type=int, default=30)
    args = parser.parse_args()
    try:
        create_backup(Path(args.destination), args.retention_days)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"BACKUP FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())