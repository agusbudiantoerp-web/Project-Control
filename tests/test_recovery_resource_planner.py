import pytest

from ai_project_control.recovery_resource_planner import estimate_resource_recovery


def test_additional_resources_reduce_duration_and_calculate_incremental_cost():
    result = estimate_resource_recovery(
        remaining_work_units=1000,
        current_daily_productivity=50,
        additional_crew_count=2,
        productivity_per_additional_crew=10,
        additional_equipment_count=1,
        productivity_per_additional_equipment=15,
        efficiency_factor=0.8,
        current_daily_cost=1_000_000,
        additional_crew_daily_cost=250_000,
        additional_equipment_daily_cost=300_000,
        currency="IDR",
    )
    assert result["status"] == "ASSESSED"
    assert result["recovery"]["daily_productivity"] == 75
    assert result["recovery"]["duration_working_days"] < result["baseline"]["duration_working_days"]
    assert result["recovery"]["days_saved"] > 0
    assert result["recovery"]["incremental_cost_vs_baseline"] > 0


def test_no_additional_resources_matches_baseline_duration():
    result = estimate_resource_recovery(
        remaining_work_units=500, current_daily_productivity=25,
    )
    assert result["recovery"]["duration_working_days"] == result["baseline"]["duration_working_days"]
    assert result["recovery"]["days_saved"] == 0


def test_added_resources_require_productivity_assumptions():
    with pytest.raises(ValueError, match="productivity_per_additional_crew"):
        estimate_resource_recovery(
            remaining_work_units=500, current_daily_productivity=25,
            additional_crew_count=1,
        )


@pytest.mark.parametrize("efficiency", [0, -0.1, 1.1, float("nan")])
def test_invalid_efficiency_rejected(efficiency):
    with pytest.raises(ValueError, match="efficiency_factor"):
        estimate_resource_recovery(
            remaining_work_units=500, current_daily_productivity=25,
            efficiency_factor=efficiency,
        )


def test_invalid_resource_counts_and_working_days_rejected():
    with pytest.raises(ValueError, match="additional_equipment_count"):
        estimate_resource_recovery(
            remaining_work_units=500, current_daily_productivity=25,
            additional_equipment_count=-1,
        )
    with pytest.raises(ValueError, match="working_days_per_week"):
        estimate_resource_recovery(
            remaining_work_units=500, current_daily_productivity=25,
            working_days_per_week=8,
        )
