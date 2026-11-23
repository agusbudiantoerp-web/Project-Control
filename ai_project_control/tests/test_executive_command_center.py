import pandas as pd

from executive_command_center import build_executive_command_center


def test_prioritizes_project_with_multiple_adverse_signals():
    portfolio = pd.DataFrame([
        {"project_id":"A","project_name":"Alpha","SPI":0.7,"CPI":0.8,
         "schedule_slip_days":25,"BAC":100,"EAC":130,"currency":"USD"},
        {"project_id":"B","project_name":"Beta","SPI":1.0,"CPI":1.0,
         "schedule_slip_days":0,"BAC":100,"EAC":100,"currency":"USD"},
    ])
    risk = pd.DataFrame([
        {"project_id":"A","risk_score":80,"risk_status":"CRITICAL","evidence":["High risk"]},
        {"project_id":"B","risk_score":5,"risk_status":"LOW","evidence":[]},
    ])
    result = build_executive_command_center(portfolio, risk)
    assert result["available"]
    assert result["queue"].iloc[0]["project_id"] == "A"
    assert result["queue"].iloc[0]["decision_tier"] == "P1 - IMMEDIATE"


def test_missing_indicators_are_unscored_not_low_risk():
    portfolio = pd.DataFrame([{"project_id":"X","project_name":"Unknown"}])
    result = build_executive_command_center(portfolio)
    assert result["queue"].iloc[0]["decision_tier"] == "UNSCORED"


def test_does_not_sum_financials_across_currencies():
    portfolio = pd.DataFrame([
        {"project_id":"A","project_name":"A","BAC":100,"EAC":120,"currency":"USD"},
        {"project_id":"B","project_name":"B","BAC":100,"EAC":120,"currency":"IDR"},
    ])
    result = build_executive_command_center(portfolio)
    assert "currency" in result["queue"]
    assert len(result["queue"]) == 2


def test_source_portfolio_is_not_mutated():
    portfolio = pd.DataFrame([{"project_id":"A","project_name":"A","SPI":0.8}])
    before = portfolio.copy(deep=True)
    build_executive_command_center(portfolio)
    pd.testing.assert_frame_equal(portfolio, before)
