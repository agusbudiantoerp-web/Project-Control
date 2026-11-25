from ai_project_control.schedule_cost_outlook import build_schedule_cost_outlook


def test_combines_cost_scenarios_and_project_finish_delay():
    result = build_schedule_cost_outlook(
        {"project_id": "P1", "PV": 800, "EV": 700, "AC": 800, "BAC": 1000, "currency": "IDR"},
        [{"activity_id": "A1", "baseline_finish_date": "2026-11-20",
          "forecast_finish_date": "2026-11-28"}],
        as_of_date="2026-11-01",
    )
    assert result["status"] == "ASSESSED"
    assert result["schedule_forecast"]["project_delay_days"] == 8
    assert result["cost_forecast"]["status"] == "ASSESSED"
    assert result["management_attention"]["cost_scenarios_over_budget"]


def test_missing_evm_and_schedule_dates_are_not_inferred():
    result = build_schedule_cost_outlook(
        {"project_id": "P1", "currency": "IDR"},
        [{"activity_id": "A1"}], as_of_date="2026-11-01",
    )
    assert result["status"] == "PARTIALLY_ASSESSED"
    assert result["cost_forecast"]["status"] == "INSUFFICIENT_DATA"
    assert result["schedule_forecast"]["project_delay_days"] is None


def test_no_inputs_is_insufficient_data():
    result = build_schedule_cost_outlook(
        {"project_id": "P1", "currency": "IDR"}, [], as_of_date="2026-11-01"
    )
    assert result["status"] == "INSUFFICIENT_DATA"


def test_rejects_invalid_input_types():
    import pytest
    with pytest.raises(TypeError):
        build_schedule_cost_outlook([], [], as_of_date="2026-11-01")
