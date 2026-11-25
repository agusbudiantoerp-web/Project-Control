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
    # TCPI is independently defined from BAC, EV and remaining budget; it remains calculable even when CPI is zero.
    assert math.isclose(result["tcpi"], 100.0 / 90.0)


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


def test_invalid_bac_type_does_not_crash_dashboard_summary():
    result = project_summary(_period(ev=10.0, ac=10.0), bac="not-a-number")
    assert math.isnan(result["bac"])
    assert math.isnan(result["eac"])
    assert math.isnan(result["percent_complete"])


def test_overflowing_spi_cpi_and_percentages_become_unavailable():
    result = project_summary(
        _period(pv=1e-308, ev=1e308, ac=1e-308),
        bac=1e308,
    )
    assert math.isnan(result["spi"])
    assert math.isnan(result["cpi"])
    assert math.isnan(result["eac"])
    assert math.isnan(result["sv_pct"])
    # CV% remains finite here: (EV - AC) / EV is approximately 100%.
    assert math.isclose(result["cv_pct"], 100.0)
