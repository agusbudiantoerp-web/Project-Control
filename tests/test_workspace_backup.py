import sqlite3

import pytest

from ai_project_control.project_store import ProjectStore
from ai_project_control.workspace_backup import build_workspace_backup


def test_backup_is_valid_and_contains_saved_project_records(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "Backup Test", "currency": "IDR", "BAC": 100,
    }])
    backup = build_workspace_backup(db)
    assert backup.startswith(b"SQLite format 3\x00")
    copy = tmp_path / "restored.sqlite3"
    copy.write_bytes(backup)
    restored = ProjectStore(copy)
    assert restored.list_project_ids() == ["P1"]
    assert restored.load_dataset("P1", "project_master")[0]["project_name"] == "Backup Test"


def test_backup_does_not_change_source(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    ProjectStore(db)
    before = db.read_bytes()
    build_workspace_backup(db)
    assert db.read_bytes() == before


def test_missing_database_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_workspace_backup(tmp_path / "missing.sqlite3")


def test_memory_database_is_not_accepted():
    with pytest.raises(ValueError, match="In-memory"):
        build_workspace_backup(":memory:")
