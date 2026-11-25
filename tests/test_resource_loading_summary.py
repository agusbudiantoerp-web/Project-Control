"""Tests for resource loading summary."""
import pytest
from ai_project_control.resource_loading_summary import build_resource_loading_summary


def test_aggregates_demand_and_flags_overload():
    result = build_resource_loading_summary([
        {"resource_id": "EXC", "period": "2026-01", "planned_units": 7, "actual_units": 8, "capacity_units": 10},
        {"resource_id": "EXC", "period": "2026-01", "planned_units": 5, "actual_units": 4, "capacity_units": 5},
    ])
    row = result["rows"].iloc[0]
    assert row["planned_units"] == 12
    assert row["capacity_units"] == 15
    assert row["planned_utilization_pct"] == pytest.approx(80)
    assert row["actual_utilization_pct"] == pytest.approx(80)
    assert row["status"] == "WITHIN_CAPACITY"


def test_marks_missing_capacity_unassessed_not_zero():
    result = build_resource_loading_summary([
        {"resource_id": "TEAM", "period": "2026-01", "planned_units": 4, "capacity_units": None},
    ])
    assert result["rows"].iloc[0]["status"] == "UNASSESSED"
    assert result["unassessed_count"] == 1


def test_flags_overload():
    result = build_resource_loading_summary([
        {"resource_id": "CRANE", "period": "W1", "planned_units": 11, "capacity_units": 10},
    ])
    assert result["overloaded_count"] == 1
    assert result["rows"].iloc[0]["status"] == "OVERLOADED"


def test_rejects_negative_or_nonfinite_values():
    with pytest.raises(ValueError):
        build_resource_loading_summary([
            {"resource_id": "R", "period": "P1", "planned_units": -1, "capacity_units": 2},
        ])


def test_empty_records_are_no_data():
    assert build_resource_loading_summary([])["status"] == "NO_DATA"


def test_rejects_boolean_resource_units_and_aggregate_overflow():
    with pytest.raises(ValueError, match="not boolean"):
        build_resource_loading_summary([
            {"resource_id": "R", "period": "P1", "planned_units": True, "capacity_units": 2},
        ])
    with pytest.raises(ValueError, match="numeric range"):
        build_resource_loading_summary([
            {"resource_id": "R", "period": "P1", "planned_units": 1e308, "capacity_units": 1e308},
            {"resource_id": "R", "period": "P1", "planned_units": 1e308, "capacity_units": 1e308},
        ])


def test_overflowing_utilization_ratio_is_unassessed():
    result = build_resource_loading_summary([{
        "resource_id": "R", "period": "P1",
        "planned_units": 1e308, "capacity_units": 1e-308,
    }])
    assert result["rows"].iloc[0]["status"] == "UNASSESSED"
    assert result["unassessed_count"] == 1
