from ai_project_control.streamlit_workspace_dashboard import _performance_display_value


def test_zero_performance_score_is_displayed_as_zero():
    assert _performance_display_value({"assessed_count": 1}, [{"performance_score": 0}]) == 0


def test_missing_performance_score_is_not_assessed():
    assert _performance_display_value({"assessed_count": 1}, [{"performance_score": None}]) == "Not assessed"


def test_unassessed_project_is_not_assessed():
    assert _performance_display_value({"assessed_count": 0}, [{"performance_score": 0}]) == "Not assessed"


import math

from ai_project_control.streamlit_workspace_dashboard import _finite_metric_display


def test_non_finite_dashboard_metrics_are_not_rendered_as_nan():
    assert _finite_metric_display(float("nan")) == "Not available"
    assert _finite_metric_display(float("inf")) == "Not available"
    assert _finite_metric_display(None) == "Not available"


def test_zero_dashboard_metric_remains_visible():
    assert _finite_metric_display(0) == "0.00"
