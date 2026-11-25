import pytest

from ai_project_control.recovery_decision_engine import build_recovery_decision_brief


def full_inputs():
    return {
        "evm": {"SPI": 0.82, "CPI": 0.91},
        "risk_exposure": {"status": "ASSESSED", "priority_summary": {"CRITICAL": 1, "HIGH": 2}},
        "risk_adjusted_outlook": {"currency": "IDR", "executive_summary": {"p80_contingency": 1500000}},
        "scenario_comparison": {"scenarios": [
            {"scenario_id": "S1", "name": "Extra crew", "assessment": "TARGET_MET",
             "duration_saving_days": 10, "incremental_cost": 100000, "risk_score": 20}
        ]},
        "resource_recovery": {"status": "ASSESSED", "currency": "IDR",
            "baseline": {"duration_working_days": 20},
            "recovery": {"duration_working_days": 15, "days_saved": 5,
                         "incremental_cost_vs_baseline": 200000}},
    }


def test_full_brief_prioritizes_signals_and_exposes_candidate():
    result = build_recovery_decision_brief(**full_inputs())
    assert result["status"] == "ASSESSED"
    assert result["signal_count"] >= 5
    assert result["signals"][0]["severity"] == "HIGH"
    assert result["recovery_scenario_candidate"]["scenario_id"] == "S1"
    assert result["resource_recovery_summary"]["days_saved"] == 5
    assert result["decision_authority"] == "PROJECT_MANAGER / PROJECT_DIRECTOR"


def test_missing_inputs_are_disclosed_and_status_is_partial():
    result = build_recovery_decision_brief(evm={"SPI": None, "CPI": None})
    assert result["status"] == "PARTIALLY_ASSESSED"
    assert "RISK_REGISTER" in result["missing_inputs"]
    assert "SPI" in result["missing_inputs"]
    assert result["recommendations"]


def test_no_inputs_is_insufficient_data():
    result = build_recovery_decision_brief()
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["signal_count"] == 0


def test_scenario_without_schedule_benefit_is_not_recommended():
    inputs = full_inputs()
    inputs["scenario_comparison"] = {"scenarios": [
        {"scenario_id": "N", "assessment": "NO_SCHEDULE_BENEFIT", "duration_saving_days": 0}
    ]}
    result = build_recovery_decision_brief(**inputs)
    assert result["recovery_scenario_candidate"] is None
    assert "NO_RECOVERY_SCENARIO_WITH_SCHEDULE_BENEFIT" in result["missing_inputs"]


@pytest.mark.parametrize("spi,cpi", [(0, 0.9), (1.2, 0.9), (0.9, float("nan"))])
def test_invalid_threshold_or_indicator_values_are_handled(spi, cpi):
    with pytest.raises(ValueError):
        build_recovery_decision_brief(
            evm={"SPI": spi, "CPI": cpi},
            spi_warning_threshold=0,
        )
    with pytest.raises(ValueError):
        build_recovery_decision_brief(evm={"SPI": float("inf"), "CPI": 1})


def test_empty_risk_register_not_interpreted_as_zero_risk():
    inputs = full_inputs()
    inputs["risk_exposure"] = {"status": "NO_RISKS", "priority_summary": {}}
    result = build_recovery_decision_brief(**inputs)
    assert "RISK_REGISTER_HAS_NO_RECORDED_RISKS" in result["missing_inputs"]
