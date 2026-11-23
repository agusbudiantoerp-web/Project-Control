import pytest

from ai_project_control.schedule_engine import calculate_critical_path


def test_calculates_critical_path_and_float():
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 3, "predecessors": []},
        {"activity_id": "B", "duration_days": 4, "predecessors": ["A"]},
        {"activity_id": "C", "duration_days": 2, "predecessors": ["A"]},
        {"activity_id": "D", "duration_days": 2, "predecessors": ["B", "C"]},
    ])
    assert result["status"] == "ASSESSED"
    assert result["project_duration_days"] == 9
    rows = {row["activity_id"]: row for row in result["activities"]}
    assert rows["B"]["total_float_days"] == 0
    assert rows["C"]["total_float_days"] == 2
    assert rows["D"]["total_float_days"] == 0
    assert result["critical_path"] == ["A", "B", "D"]


def test_rejects_missing_predecessor_reference():
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 2, "predecessors": ["UNKNOWN"]}
    ])
    assert result["status"] == "INVALID_DEPENDENCIES"
    assert result["project_duration_days"] is None


def test_detects_dependency_cycle():
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 1, "predecessors": ["B"]},
        {"activity_id": "B", "duration_days": 1, "predecessors": ["A"]},
    ])
    assert result["status"] == "CYCLIC_DEPENDENCIES"
    assert result["critical_path"] == []


@pytest.mark.parametrize("duration", [-1, float("inf"), "bad"])
def test_rejects_invalid_duration(duration):
    with pytest.raises(ValueError):
        calculate_critical_path([{"activity_id": "A", "duration_days": duration}])


def test_rejects_duplicate_activity_ids():
    with pytest.raises(ValueError, match="Duplicate"):
        calculate_critical_path([
            {"activity_id": "A", "duration_days": 1},
            {"activity_id": "A", "duration_days": 2},
        ])


def test_empty_schedule_is_not_a_zero_day_project():
    result = calculate_critical_path([])
    assert result["status"] == "NO_ACTIVITIES"
    assert result["project_duration_days"] is None
