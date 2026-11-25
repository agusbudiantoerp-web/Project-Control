"""Smoke test for the repository-root unified Streamlit application."""
from streamlit.testing.v1 import AppTest


def test_primary_workspace_app_renders_without_uncaught_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_CONTROL_DB", str(tmp_path / "workspace.sqlite3"))
    app = AppTest.from_file("app.py", default_timeout=45).run()
    assert not app.exception, "\n".join(str(error.message) for error in app.exception)
