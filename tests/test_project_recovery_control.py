import pytest

from ai_project_control.project_recovery_control import assess_recovery_control


def test_recovery_gap_detects_schedule_spi_and_budget_shortfalls():
    result = assess_recovery_control(
        baseline_finish="2026-12-01",
        current_forecast_finish="2026-12-20",
        recovery_target_finish="2026-12-10",
        current_spi=0.82,
        target_spi=0.95,
        approved_recovery_budget=100_000,
        estimated_recovery_cost=125_000,
    )
    assert result["status"] == "RECOVERY_GAP"
    assert result["baseline_variance_days"] == 19
    assert result["recovery_target_gap_days"] == 10
    assert result["spi_gap"] == 0.13
    assert result["funding_gap"] == 25_000


def test_targets_met_when_all_supplied_targets_are_met():
    result = assess_recovery_control(
        baseline_finish="2026-12-01",
        current_forecast_finish="2026-11-30",
        recovery_target_finish="2026-12-01",
        current_spi=1.02,
        target_spi=0.95,
        approved_recovery_budget=200,
        estimated_recovery_cost=150,
    )
    assert result["status"] == "TARGETS_MET"
    assert result["recovery_target_gap_days"] == -1
    assert result["funding_gap"] == -50


def test_missing_inputs_are_explicit_and_not_assumed_met():
    result = assess_recovery_control(
        baseline_finish="2026-12-01",
        current_forecast_finish="2026-12-20",
    )
    assert result["status"] == "INCOMPLETE_INPUT"
    assert "recovery_target_finish" in result["missing_inputs"]
    assert result["funding_gap"] is None


@pytest.mark.parametrize("value", ["not-a-date", "2026-15-01"])
def test_invalid_dates_rejected(value):
    with pytest.raises(ValueError, match="baseline_finish"):
        assess_recovery_control(
            baseline_finish=value,
            current_forecast_finish="2026-12-20",
        )


@pytest.mark.parametrize("field,value", [
    ("current_spi", -0.1),
    ("target_spi", -0.1),
    ("approved_recovery_budget", -1),
    ("estimated_recovery_cost", -1),
])
def test_negative_values_rejected(field, value):
    args = {
        "baseline_finish": "2026-12-01",
        "current_forecast_finish": "2026-12-20",
        "current_spi": 0.9,
        "target_spi": 0.95,
        "approved_recovery_budget": 100,
        "estimated_recovery_cost": 90,
    }
    args[field] = value
    with pytest.raises(ValueError):
        assess_recovery_control(**args)
