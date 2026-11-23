from ai_project_control.integrated_forecast import build_integrated_forecast


def test_integrates_cost_scenarios_and_explicit_schedule_delay():
    result = build_integrated_forecast(
        evm_snapshot={"project_id": "P1", "PV": 800, "EV": 700, "AC": 800, "BAC": 1000, "currency": "IDR"},
        schedule_activities=[{
            "activity_id": "A1", "baseline_finish_date": "2026-11-20",
            "forecast_finish_date": "2026-11-28",
        }],
        as_of_date="2026-11-01",
    )
    assert result["status"] == "ASSESSED"
    assert result["schedule_forecast"]["project_delay_days"] == 8
    assert result["cost_forecast"]["status"] == "ASSESSED"
    assert result["management_attention"]["cost_scenarios_over_budget"]


def test_missing_schedule_and_cost_data_are_not_invented():
    result = build_integrated_forecast(
        evm_snapshot={"project_id": "P1", "currency": "IDR"},
        schedule_activities=[{"activity_id": "A1"}],
        as_of_date="2026-11-01",
    )
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["cost_forecast"]["status"] == "INSUFFICIENT_DATA"
    assert result["schedule_forecast"]["project_delay_days"] is None


def test_partial_schedule_keeps_project_finish_unassessed():
    result = build_integrated_forecast(
        evm_snapshot={"project_id": "P1", "PV": 100, "EV": 90, "AC": 100, "BAC": 200, "currency": "IDR"},
        schedule_activities=[
            {"activity_id": "A1", "baseline_finish_date": "2026-11-10", "forecast_finish_date": "2026-11-12"},
            {"activity_id": "A2", "planned_progress_pct": 50, "actual_progress_pct": 40},
        ],
        as_of_date="2026-11-01",
    )
    assert result["status"] == "PARTIALLY_ASSESSED"
    assert result["schedule_forecast"]["project_forecast_finish_date"] is None
