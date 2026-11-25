from pathlib import Path

import core


def test_streamlit_app_renders_without_runtime_exceptions(tmp_path, monkeypatch):
    """Smoke-test the actual Streamlit entry point with an isolated local database."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(core, "DB_PATH", tmp_path / "project_control_smoke.db")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=60).run()

    assert not app.exception, "\n".join(str(item.message) for item in app.exception)
