import pytest

from ai_project_control.recovery_scenario_comparator import compare_recovery_scenarios


def test_scenarios_rank_by_cost_per_day_saved():
    result = compare_recovery_scenarios([
        {"scenario_id": "B", "name": "Second shift", "duration_saving_days": 10,
         "incremental_cost": 100_000, "risk_score": 35},
        {"scenario_id": "A", "name": "Extra crew", "duration_saving_days": 8,
         "incremental_cost": 40_000, "risk_score": 25},
    ], current_forecast_duration_days=100, target_duration_days=95)
    assert result["scenarios"][0]["scenario_id"] == "A"
    assert result["scenarios"][0]["cost_per_day_saved"] == 5000
    assert result["summary"]["scenario_count"] == 2


def test_target_met_and_target_not_met_are_explicit():
    result = compare_recovery_scenarios([
        {"scenario_id": "FAST", "name": "Fast track", "duration_saving_days": 20,
         "incremental_cost": 200, "risk_score": 40},
        {"scenario_id": "SLOW", "name": "Small crew", "duration_saving_days": 5,
         "incremental_cost": 100, "risk_score": 10},
    ], current_forecast_duration_days=100, target_duration_days=90)
    by_id = {row["scenario_id"]: row for row in result["scenarios"]}
    assert by_id["FAST"]["target_met"] is True
    assert by_id["SLOW"]["target_met"] is False


def test_zero_saving_has_no_cost_efficiency_ratio():
    result = compare_recovery_scenarios([
        {"scenario_id": "N", "name": "No change", "duration_saving_days": 0,
         "incremental_cost": 0, "risk_score": 0},
    ], current_forecast_duration_days=50)
    assert result["scenarios"][0]["cost_per_day_saved"] is None
    assert result["scenarios"][0]["assessment"] == "NO_SCHEDULE_BENEFIT"


def test_duplicate_ids_and_invalid_values_are_rejected():
    duplicate = [
        {"scenario_id": "X", "name": "One", "duration_saving_days": 1, "incremental_cost": 1, "risk_score": 1},
        {"scenario_id": "X", "name": "Two", "duration_saving_days": 2, "incremental_cost": 2, "risk_score": 2},
    ]
    with pytest.raises(ValueError, match="unique"):
        compare_recovery_scenarios(duplicate, current_forecast_duration_days=10)
    with pytest.raises(ValueError, match="risk_score"):
        compare_recovery_scenarios([
            {"scenario_id": "Y", "name": "Bad risk", "duration_saving_days": 1,
             "incremental_cost": 1, "risk_score": 101},
        ], current_forecast_duration_days=10)


@pytest.mark.parametrize("duration", [0, -1, "bad"])
def test_invalid_current_duration_rejected(duration):
    with pytest.raises(ValueError):
        compare_recovery_scenarios([], current_forecast_duration_days=duration)
