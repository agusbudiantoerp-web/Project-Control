from pathlib import Path

from ai_project_control.workspace_config import (
    DEFAULT_WORKSPACE_DATABASE,
    get_workspace_database_path,
)


def test_workspace_database_path_uses_one_environment_override(monkeypatch, tmp_path):
    configured = tmp_path / "shared" / "project.sqlite3"
    monkeypatch.setenv("PROJECT_CONTROL_DB", str(configured))
    assert get_workspace_database_path() == str(configured)


def test_blank_workspace_database_override_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("PROJECT_CONTROL_DB", "   ")
    assert get_workspace_database_path() == str(Path(DEFAULT_WORKSPACE_DATABASE))
