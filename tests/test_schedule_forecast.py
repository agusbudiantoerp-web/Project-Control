import pytest

from ai_project_control.schedule_forecast import assess_schedule_delays


def test_reports_explicit_finish_date_delay():
    result = assess_schedule_delays([
        {"activity_id": "A", "baseline_finish_date": "2026-11-10", "forecast_finish_date": "2026-11-15"}
    ], as_of_date="2026-11-01")
    assert result["status"] == "ASSESSED"
    assert result["activities"][0]["delay_days"] == 5
    assert result["delayed_activity_ids"] == ["A"]
    assert result["project_delay_days"] == 5


def test_progress_variance_is_percentage_points_not_days():
    result = assess_schedule_delays([
        {"activity_id": "A", "planned_progress_pct": 60, "actual_progress_pct": 48}
    ], as_of_date="2026-11-01")
    row = result["activities"][0]
    assert row["progress_variance_pp"] == -12
    assert row["status"] == "BEHIND_PROGRESS"
    assert row["delay_days"] is None
    assert result["project_delay_days"] is None


def test_missing_fields_are_not_assumed_on_track():
    result = assess_schedule_delays([{"activity_id": "A"}], as_of_date="2026-11-01")
    assert result["status"] == "PARTIALLY_ASSESSED"
    assert result["unassessed_activity_ids"] == ["A"]
    assert result["activities"][0]["status"] == "INSUFFICIENT_DATA"


def test_project_finish_not_claimed_if_any_activity_has_no_dates():
    result = assess_schedule_delays([
        {"activity_id": "A", "baseline_finish_date": "2026-11-10", "forecast_finish_date": "2026-11-12"},
        {"activity_id": "B", "planned_progress_pct": 20, "actual_progress_pct": 20},
    ], as_of_date="2026-11-01")
    assert result["project_baseline_finish_date"] is None
    assert result["project_forecast_finish_date"] is None
    assert result["project_delay_days"] is None


@pytest.mark.parametrize("pct", [-1, 101, "bad"])
def test_rejects_invalid_progress_percent(pct):
    with pytest.raises(ValueError):
        assess_schedule_delays([{"activity_id": "A", "actual_progress_pct": pct}], as_of_date="2026-11-01")


def test_rejects_invalid_date_and_duplicate_ids():
    with pytest.raises(ValueError):
        assess_schedule_delays([{"activity_id": "A", "forecast_finish_date": "not-a-date"}], as_of_date="2026-11-01")
    with pytest.raises(ValueError, match="Duplicate"):
        assess_schedule_delays([{"activity_id": "A"}, {"activity_id": "A"}], as_of_date="2026-11-01")
