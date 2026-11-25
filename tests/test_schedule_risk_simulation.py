import pytest

from ai_project_control.schedule_risk_simulation import simulate_schedule_risk


def activities():
    return [
        {"activity_id": "A", "predecessors": [], "duration_min_days": 8,
         "duration_most_likely_days": 10, "duration_max_days": 12},
        {"activity_id": "B", "predecessors": ["A"], "duration_min_days": 4,
         "duration_most_likely_days": 5, "duration_max_days": 6},
        {"activity_id": "C", "predecessors": [], "duration_min_days": 6,
         "duration_most_likely_days": 7, "duration_max_days": 8},
    ]


def test_schedule_simulation_is_reproducible_and_reports_percentiles():
    result = simulate_schedule_risk(activities(), [], "2026-11-01", iterations=1000, seed=7)
    assert result == simulate_schedule_risk(activities(), [], "2026-11-01", iterations=1000, seed=7)
    assert result["status"] == "ASSESSED"
    assert result["finish_date"]["p50"] <= result["finish_date"]["p80"] <= result["finish_date"]["p90"]


def test_activity_linked_risk_increases_schedule_duration():
    risk = [{"risk_id": "R1", "activity_id": "A", "probability": 1,
             "delay_min_days": 3, "delay_most_likely_days": 3, "delay_max_days": 3}]
    base = simulate_schedule_risk(activities(), [], "2026-11-01", iterations=1000)
    with_risk = simulate_schedule_risk(activities(), risk, "2026-11-01", iterations=1000)
    assert with_risk["duration_days"]["p50"] >= base["duration_days"]["p50"] + 2.9


def test_unknown_predecessor_and_dependency_cycle_rejected():
    bad = [{"activity_id": "A", "predecessors": ["X"], "duration_min_days": 1,
            "duration_most_likely_days": 1, "duration_max_days": 1}]
    with pytest.raises(ValueError, match="unknown predecessors"):
        simulate_schedule_risk(bad, [], "2026-11-01", iterations=1000)
    cycle = [
        {"activity_id": "A", "predecessors": ["B"], "duration_min_days": 1, "duration_most_likely_days": 1, "duration_max_days": 1},
        {"activity_id": "B", "predecessors": ["A"], "duration_min_days": 1, "duration_most_likely_days": 1, "duration_max_days": 1},
    ]
    with pytest.raises(ValueError, match="cycle"):
        simulate_schedule_risk(cycle, [], "2026-11-01", iterations=1000)


def test_risk_must_reference_known_activity_and_valid_probability():
    risk = [{"risk_id": "R1", "activity_id": "MISSING", "probability": .5,
             "delay_min_days": 1, "delay_most_likely_days": 2, "delay_max_days": 3}]
    with pytest.raises(ValueError, match="known activity"):
        simulate_schedule_risk(activities(), risk, "2026-11-01", iterations=1000)


def test_empty_activity_network_is_not_zero_duration():
    result = simulate_schedule_risk([], [], "2026-11-01", iterations=1000)
    assert result["status"] == "NO_ACTIVITIES"


def test_invalid_distribution_rejected():
    bad = [{"activity_id": "A", "duration_min_days": 5,
            "duration_most_likely_days": 3, "duration_max_days": 8}]
    with pytest.raises(ValueError, match="durations"):
        simulate_schedule_risk(bad, [], "2026-11-01", iterations=1000)


def test_schedule_risk_rejects_boolean_numeric_inputs():
    bad = [{**activities()[0], "duration_min_days": True}]
    with pytest.raises(ValueError, match="not boolean"):
        simulate_schedule_risk(bad, [], "2026-11-01", iterations=1000)


def test_schedule_risk_normalizes_datetime_project_start():
    from datetime import datetime

    result = simulate_schedule_risk(
        activities(), [], datetime(2026, 11, 1, 12, 30), iterations=1000
    )
    assert result["project_start_date"] == "2026-11-01"


def test_schedule_risk_rejects_overflowing_sampled_finish():
    huge = [{
        "activity_id": "A", "predecessors": [],
        "duration_min_days": 1e308,
        "duration_most_likely_days": 1e308,
        "duration_max_days": 1e308,
    }, {
        "activity_id": "B", "predecessors": ["A"],
        "duration_min_days": 1e308,
        "duration_most_likely_days": 1e308,
        "duration_max_days": 1e308,
    }]
    with pytest.raises(ValueError, match="supported numeric range"):
        simulate_schedule_risk(huge, [], "2026-11-01", iterations=1000)


def test_schedule_risk_rejects_finish_date_outside_calendar_range():
    very_long = [{
        "activity_id": "A", "predecessors": [],
        "duration_min_days": 10_000_000,
        "duration_most_likely_days": 10_000_000,
        "duration_max_days": 10_000_000,
    }]
    with pytest.raises(ValueError, match="calendar range"):
        simulate_schedule_risk(very_long, [], "2026-11-01", iterations=1000)
