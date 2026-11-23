import pytest
from ai_project_control.cost_forecast import build_cost_forecast


def evm():
    return {"PV": 800, "EV": 700, "AC": 800, "BAC": 1000, "currency": "IDR"}


def test_builds_three_cost_forecast_scenarios():
    result = build_cost_forecast(evm())
    assert result["status"] == "ASSESSED"
    assert result["scenarios"][0]["EAC"] == pytest.approx(1142.86)
    assert result["scenarios"][1]["EAC"] == 1100
    assert result["scenarios"][2]["EAC"] == pytest.approx(1191.84)
    assert result["scenarios"][0]["status"] == "OVER_BUDGET"


def test_missing_currency_is_not_assumed():
    data = evm()
    data["currency"] = ""
    result = build_cost_forecast(data)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert "CURRENCY" in result["data_gaps"]


def test_missing_evm_inputs_are_not_zero():
    result = build_cost_forecast({"currency": "IDR"})
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["scenarios"] == []


def test_eac_scenario_with_zero_cpi_is_unassessed():
    data = {"PV": 100, "EV": 0, "AC": 100, "BAC": 500, "currency": "IDR"}
    result = build_cost_forecast(data)
    assert result["scenarios"][0]["status"] == "UNASSESSED"
    assert result["scenarios"][2]["status"] == "UNASSESSED"
    assert result["scenarios"][1]["EAC"] == 600


def test_ev_above_bac_requires_review():
    data = {"PV": 100, "EV": 120, "AC": 100, "BAC": 100, "currency": "IDR"}
    result = build_cost_forecast(data)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "EV_EXCEEDS_BAC" in result["data_gaps"]


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        build_cost_forecast(evm(), warning_threshold_pct=-1)
