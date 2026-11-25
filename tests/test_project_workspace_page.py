from pathlib import Path


def test_project_workspace_page_renders_with_isolated_database(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("PROJECT_CONTROL_DB", str(tmp_path / "workspace.sqlite3"))
    page_path = Path(__file__).resolve().parents[1] / "pages" / "01_Project_Workspace.py"
    app = AppTest.from_file(str(page_path), default_timeout=90).run()

    assert not app.exception, "\n".join(str(item.message) for item in app.exception)
