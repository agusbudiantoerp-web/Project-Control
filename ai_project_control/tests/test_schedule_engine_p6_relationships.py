import pytest

from ai_project_control.schedule_engine import calculate_critical_path


@pytest.mark.parametrize(
    "kind,lag,expected_start,expected_finish",
    [
        ("FS", 0, 5, 9),
        ("SS", 0, 0, 5),
        ("FF", 0, 1, 5),
        ("SF", 0, 0, 5),
        ("FS", 2, 7, 11),
        ("FS", -2, 3, 7),
        ("SS", 1, 1, 5),
        ("FF", -1, 0, 5),
    ],
)
def test_cpm_honors_all_p6_relationship_types_and_signed_lag(
    kind, lag, expected_start, expected_finish
):
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 5},
        {
            "activity_id": "B",
            "duration_days": 4,
            "predecessor_relationships": [{
                "predecessor_id": "A",
                "relationship_type": kind,
                "lag_days": lag,
            }],
        },
    ])

    assert result["status"] == "ASSESSED"
    by_id = {row["activity_id"]: row for row in result["activities"]}
    assert by_id["B"]["early_start"] == pytest.approx(expected_start)
    assert result["project_duration_days"] == pytest.approx(expected_finish)
    assert by_id["A"]["total_float_days"] >= -1e-9
    assert by_id["B"]["total_float_days"] >= -1e-9


def test_cpm_keeps_legacy_predecessor_ids_as_zero_lag_fs():
    result = calculate_critical_path([
        {"activity_id": "A", "duration_days": 5},
        {"activity_id": "B", "duration_days": 4, "predecessor_ids": "A"},
    ])
    assert result["status"] == "ASSESSED"
    assert result["project_duration_days"] == 9
    assert result["critical_path"] == ["A", "B"]


def test_cpm_rejects_unknown_relationship_type_and_cycles():
    invalid = calculate_critical_path([
        {"activity_id": "A", "duration_days": 1},
        {"activity_id": "B", "duration_days": 1,
         "predecessor_relationships": [{
             "predecessor_id": "A", "relationship_type": "XY", "lag_days": 0
         }]},
    ])
    assert invalid["status"] == "INVALID_DEPENDENCIES"

    cyclic = calculate_critical_path([
        {"activity_id": "A", "duration_days": 1, "predecessor_ids": "B"},
        {"activity_id": "B", "duration_days": 1, "predecessor_ids": "A"},
    ])
    assert cyclic["status"] == "CYCLIC_DEPENDENCIES"
