from datetime import datetime, timedelta, timezone
import importlib.util
import sqlite3
from pathlib import Path

from ai_project_control.project_store import ProjectStore


def _load_backup_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "backup_workspace.py"
    spec = importlib.util.spec_from_file_location("project_control_backup_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backup_script_creates_integrity_checked_timestamped_copy(tmp_path, monkeypatch):
    database = tmp_path / "workspace.sqlite3"
    store = ProjectStore(database)
    store.save_dataset("P1", "project_master", [{"project_id": "P1", "project_name": "Test"}])
    store.close()
    module = _load_backup_script()
    monkeypatch.setattr(module, "get_workspace_database_path", lambda: str(database))

    target = module.create_backup(tmp_path / "backups", 30)

    assert target.is_file()
    assert target.read_bytes().startswith(b"SQLite format 3\x00")
    with sqlite3.connect(target) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT COUNT(*) FROM project_records").fetchone()[0] == 1


def test_backup_script_removes_only_expired_generated_backups(tmp_path, monkeypatch):
    database = tmp_path / "workspace.sqlite3"
    ProjectStore(database).close()
    module = _load_backup_script()
    monkeypatch.setattr(module, "get_workspace_database_path", lambda: str(database))
    destination = tmp_path / "backups"
    destination.mkdir()
    expired = destination / "ai_project_control_20200101T000000000000Z.sqlite3"
    unrelated = destination / "keep-me.sqlite3"
    non_generated = destination / "ai_project_control_manual.sqlite3"
    expired.write_bytes(b"old backup")
    unrelated.write_bytes(b"unrelated file")
    non_generated.write_bytes(b"operator file")
    old_time = (datetime.now(timezone.utc) - timedelta(days=90)).timestamp()
    import os
    os.utime(expired, (old_time, old_time))

    module.create_backup(destination, 30)

    assert not expired.exists()
    assert unrelated.exists()
    assert non_generated.exists()


def test_backup_script_rejects_invalid_retention_and_missing_database(tmp_path, monkeypatch):
    module = _load_backup_script()
    with __import__("pytest").raises(ValueError, match="retention_days"):
        module.create_backup(tmp_path / "backups", 0)
    missing = tmp_path / "missing.sqlite3"
    monkeypatch.setattr(module, "get_workspace_database_path", lambda: str(missing))
    with __import__("pytest").raises(FileNotFoundError, match="Workspace database not found"):
        module.create_backup(tmp_path / "backups", 30)

def test_backup_script_rejects_workspace_database_parent_as_destination(tmp_path, monkeypatch):
    database = tmp_path / ".project_control" / "project_control.sqlite3"
    database.parent.mkdir()
    ProjectStore(database).close()
    module = _load_backup_script()
    monkeypatch.setattr(module, "get_workspace_database_path", lambda: str(database))
    with __import__("pytest").raises(ValueError, match="cannot be the workspace database"):
        module.create_backup(database.parent, 30)
