"""Regression tests for invalid EVM forecast denominators in dashboard metrics."""
import math

import pandas as pd

from ai_project_control.dashboard_metrics import project_summary


def _period(*, pv=10.0, ev=0.0, ac=10.0):
    return pd.DataFrame([{
        "period_label": pd.Timestamp("2026-11-01"),
        "planned_value_cum": pv,
        "earned_value_cum": ev,
        "actual_cost_cum": ac,
    }])


def test_zero_cpi_does_not_crash_or_publish_infinite_eac():
    result = project_summary(_period(ev=0.0, ac=10.0), bac=100.0)
    assert result["cpi"] == 0.0
    assert math.isnan(result["eac"])
    assert math.isnan(result["etc"])
    assert math.isnan(result["vac"])
    assert math.isnan(result["tcpi"])


def test_zero_actual_cost_does_not_publish_infinite_eac():
    result = project_summary(_period(ev=10.0, ac=0.0), bac=100.0)
    assert math.isnan(result["cpi"])
    assert math.isnan(result["eac"])
    assert math.isnan(result["etc"])


def test_zero_bac_does_not_publish_percent_complete_or_forecast():
    result = project_summary(_period(pv=10.0, ev=5.0, ac=5.0), bac=0.0)
    assert math.isnan(result["percent_complete"])
    assert math.isnan(result["eac"])
    assert math.isnan(result["vac"])
