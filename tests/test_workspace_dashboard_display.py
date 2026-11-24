from ai_project_control.streamlit_workspace_dashboard import _performance_display_value


def test_zero_performance_score_is_displayed_as_zero():
    assert _performance_display_value({"assessed_count": 1}, [{"performance_score": 0}]) == 0


def test_missing_performance_score_is_not_assessed():
    assert _performance_display_value({"assessed_count": 1}, [{"performance_score": None}]) == "Not assessed"


def test_unassessed_project_is_not_assessed():
    assert _performance_display_value({"assessed_count": 0}, [{"performance_score": 0}]) == "Not assessed"
