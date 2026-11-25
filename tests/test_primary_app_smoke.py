"""Smoke tests for the repository-root unified Streamlit application."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _run_page(path: Path, tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_CONTROL_DB", str(tmp_path / "workspace.sqlite3"))
    app = AppTest.from_file(str(path), default_timeout=45).run()
    assert not app.exception, "\n".join(str(error.message) for error in app.exception)


def test_primary_workspace_app_renders_without_uncaught_exception(tmp_path, monkeypatch):
    _run_page(ROOT / "app.py", tmp_path, monkeypatch)


@pytest.mark.parametrize(
    "page_name",
    [
        "01_Project_Workspace.py",
        "02_Dated_Cash_Flow.py",
        "03_EVM_Cost_Control.py",
        "04_Telegram_Executive_Report.py",
        "05_Saved_Project_Financial_Control.py",
        "06_Saved_Portfolio_COO_Cockpit.py",
    ],
)
def test_primary_operational_pages_render_without_uncaught_exception(
    page_name, tmp_path, monkeypatch
):
    _run_page(ROOT / "pages" / page_name, tmp_path, monkeypatch)


def test_primary_xer_and_drawing_intake_page_starts_without_exception(tmp_path, monkeypatch):
    _run_page(ROOT / "pages" / "08_Primavera_XER_Drawing_BOQ_Intake.py", tmp_path, monkeypatch)


def test_primary_backup_and_restore_page_starts_without_exception(tmp_path, monkeypatch):
    _run_page(ROOT / "pages" / "07_Workspace_Backup_Audit.py", tmp_path, monkeypatch)
