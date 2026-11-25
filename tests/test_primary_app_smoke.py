"""Smoke test for the repository-root unified Streamlit application."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_primary_workspace_app_renders_without_uncaught_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_CONTROL_DB", str(tmp_path / "workspace.sqlite3"))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=45).run()
    assert not app.exception, "\n".join(str(error.message) for error in app.exception)


def test_primary_xer_and_drawing_intake_page_starts_without_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_CONTROL_DB", str(tmp_path / "workspace.sqlite3"))
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "pages" / "08_Primavera_XER_Drawing_BOQ_Intake.py"),
        default_timeout=45,
    ).run()
    assert not app.exception, "\\n".join(str(error.message) for error in app.exception)


def test_primary_backup_and_restore_page_starts_without_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_CONTROL_DB", str(tmp_path / "workspace.sqlite3"))
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "pages" / "07_Workspace_Backup_Audit.py"),
        default_timeout=45,
    ).run()
    assert not app.exception, "\\n".join(str(error.message) for error in app.exception)
