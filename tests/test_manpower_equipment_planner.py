"""Tests for manpower and equipment capacity planning."""
import pytest
from ai_project_control.manpower_equipment_planner import build_manpower_equipment_plan


def test_keeps_manpower_and_equipment_separate():
    result = build_manpower_equipment_plan([
        {"resource_type": "MANPOWER", "resource_id": "OP", "resource_name": "Operator",
         "unit": "person", "period": "2026-01", "planned_units": 8, "actual_units": 7, "capacity_units": 10},
        {"resource_type": "EQUIPMENT", "resource_id": "EXC", "resource_name": "Excavator",
         "unit": "hour", "period": "2026-01", "planned_units": 12, "actual_units": 9, "capacity_units": 10},
    ])
    assert len(result["rows"]) == 2
    assert set(result["rows"]["resource_type"]) == {"MANPOWER", "EQUIPMENT"}
    assert result["overloaded_count"] == 1


def test_aggregates_same_resource_unit_and_period():
    result = build_manpower_equipment_plan([
        {"resource_type": "MANPOWER", "resource_id": "OP", "unit": "person",
         "period": "W1", "planned_units": 3, "capacity_units": 5},
        {"resource_type": "MANPOWER", "resource_id": "OP", "unit": "person",
         "period": "W1", "planned_units": 2, "capacity_units": 5},
    ])
    assert len(result["rows"]) == 1
    assert result["rows"].iloc[0]["planned_units"] == 5
    assert result["rows"].iloc[0]["capacity_units"] == 10


def test_missing_capacity_is_unassessed():
    result = build_manpower_equipment_plan([
        {"resource_type": "EQUIPMENT", "resource_id": "CRANE", "period": "W1",
         "planned_units": 4, "capacity_units": None},
    ])
    assert result["rows"].iloc[0]["status"] == "UNASSESSED"


def test_rejects_unknown_resource_type():
    with pytest.raises(ValueError, match="Unsupported resource_type"):
        build_manpower_equipment_plan([
            {"resource_type": "VEHICLE", "resource_id": "TRK", "period": "W1",
             "planned_units": 2, "capacity_units": 3},
        ])


def test_rejects_negative_demand():
    with pytest.raises(ValueError):
        build_manpower_equipment_plan([
            {"resource_type": "MANPOWER", "resource_id": "OP", "period": "W1",
             "planned_units": -2, "capacity_units": 3},
        ])


def test_empty_data_is_not_zero_capacity():
    assert build_manpower_equipment_plan([])["status"] == "NO_DATA"
