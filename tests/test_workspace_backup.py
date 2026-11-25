import sqlite3

import pytest

from ai_project_control.project_store import ProjectStore
from ai_project_control.workspace_backup import build_workspace_backup
from ai_project_control.workspace_restore import (
    restore_workspace_backup,
    validate_workspace_backup,
)


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


def test_validate_backup_reports_project_and_record_counts(tmp_path):
    db = tmp_path / "source.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "One", "currency": "IDR",
    }])
    backup = build_workspace_backup(db)
    assert validate_workspace_backup(backup) == {"project_count": 1, "record_count": 1}


def test_restore_replaces_workspace_and_keeps_pre_restore_safety_copy(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    current = ProjectStore(db)
    current.save_dataset("OLD", "project_master", [{
        "project_id": "OLD", "project_name": "Old workspace", "currency": "IDR",
    }])

    source_db = tmp_path / "source.sqlite3"
    source = ProjectStore(source_db)
    source.save_dataset("NEW", "project_master", [{
        "project_id": "NEW", "project_name": "Restored workspace", "currency": "IDR",
    }])
    backup = build_workspace_backup(source_db)

    result = restore_workspace_backup(db, backup)
    restored = ProjectStore(db)
    assert result["status"] == "RESTORED"
    assert result["project_count"] == 1
    assert restored.list_project_ids() == ["NEW"]
    assert result["safety_backup_path"]
    safety = ProjectStore(result["safety_backup_path"])
    assert safety.list_project_ids() == ["OLD"]


def test_invalid_restore_does_not_change_current_workspace(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "Keep me", "currency": "IDR",
    }])
    with pytest.raises(ValueError, match="not a SQLite database"):
        restore_workspace_backup(db, b"not a database")
    assert ProjectStore(db).list_project_ids() == ["P1"]


def test_restore_creates_new_workspace_when_destination_is_missing(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    source = ProjectStore(source_db)
    source.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "New", "currency": "IDR",
    }])
    backup = build_workspace_backup(source_db)
    destination = tmp_path / "new" / "workspace.sqlite3"
    result = restore_workspace_backup(destination, backup)
    assert result["status"] == "RESTORED"
    assert result["safety_backup_path"] is None
    assert ProjectStore(destination).list_project_ids() == ["P1"]


def test_restore_rejects_future_schema_without_touching_destination(tmp_path):
    future = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(future)
    connection.executescript(
        "CREATE TABLE project_records (project_id TEXT, dataset TEXT, record_key TEXT, payload_json TEXT, updated_at TEXT);"
        "CREATE TABLE import_events (event_id TEXT, project_id TEXT, dataset TEXT, mode TEXT, row_count INTEGER, imported_at TEXT, status TEXT, details_json TEXT);"
        "CREATE TABLE store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        "INSERT INTO store_metadata(key, value) VALUES ('schema_version', '999');"
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="schema version 999"):
        validate_workspace_backup(future.read_bytes())
