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


def test_rejects_boolean_duration_and_cumulative_overflow():
    with pytest.raises(ValueError, match="not boolean"):
        calculate_critical_path([{"activity_id": "A", "duration_days": True}])
    with pytest.raises(ValueError, match="overflow"):
        calculate_critical_path([
            {"activity_id": "A", "duration_days": 1e308},
            {"activity_id": "B", "duration_days": 1e308, "predecessors": ["A"]},
        ])


@pytest.mark.parametrize(
    ("relation_type", "lag_days", "expected_successor_start"),
    [("FS", 1, 11), ("SS", 1, 1), ("FF", 1, 6), ("SF", 8, 3)],
)
def test_supports_typed_relationships_and_signed_lags(relation_type, lag_days, expected_successor_start):
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 10},
        {
            "activity_id": "B",
            "duration_days": 5,
            "relationship_details": [{
                "predecessor_id": "A", "type": relation_type, "lag_days": lag_days,
            }],
        },
    ])
    assert result["status"] == "ASSESSED"
    rows = {row["activity_id"]: row for row in result["activities"]}
    assert rows["B"]["early_start"] == expected_successor_start
    assert rows["B"]["early_finish"] == expected_successor_start + 5


def test_legacy_predecessor_ids_remain_zero_lag_finish_to_start():
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 2},
        {"activity_id": "B", "duration_days": 3, "predecessor_ids": "A"},
    ])
    rows = {row["activity_id"]: row for row in result["activities"]}
    assert rows["B"]["early_start"] == 2
    assert rows["B"]["relationships"] == [{
        "predecessor_id": "A", "type": "FS", "lag_days": 0.0,
    }]
 
 
def test_negative_relationship_lag_is_supported():
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 10},
        {
            "activity_id": "B",
            "duration_days": 5,
            "relationship_details": [{
                "predecessor_id": "A", "type": "FS", "lag_days": -1,
            }],
        },
    ])
    rows = {row["activity_id"]: row for row in result["activities"]}
    assert rows["B"]["early_start"] == 9
    assert rows["B"]["early_finish"] == 14


def test_invalid_relationship_type_and_duplicate_predecessor_are_reported():
    invalid = calculate_critical_path([
        {"activity_id": "A", "duration_days": 1},
        {"activity_id": "B", "duration_days": 1, "relationship_details": [
            {"predecessor_id": "A", "type": "XX", "lag_days": 0},
        ]},
    ])
    assert invalid["status"] == "INVALID_DEPENDENCIES"
    with pytest.raises(ValueError, match="unsupported relationship type"):
        calculate_critical_path([
            {"activity_id": "A", "duration_days": 1},
            {"activity_id": "B", "duration_days": 1, "relationship_details": [
                {"predecessor_id": "A", "type": "XX", "lag_days": 0},
            ]},
        ])
