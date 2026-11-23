import pytest
from ai_project_control.boq_schedule_resource_integration import build_boq_schedule_resource_integration


def sample():
    boq = [
        {"boq_id": "B1", "activity_id": "A", "quantity": 10, "unit": "m3", "unit_rate": 5},
        {"boq_id": "B2", "activity_id": "A", "quantity": 2, "unit": "day", "amount": 30},
    ]
    activities = [
        {"activity_id": "A", "duration_days": 3},
        {"activity_id": "B", "duration_days": 2, "predecessors": ["A"]},
    ]
    resources = [
        {"resource_id": "EX1", "activity_id": "A", "resource_type": "EQUIPMENT",
         "planned_units": 12, "capacity_units": 15, "unit": "hour"},
    ]
    return boq, activities, resources


def test_links_boq_schedule_and_resources():
    boq, activities, resources = sample()
    result = build_boq_schedule_resource_integration(boq, activities, resources)
    row = result["rows"][0]
    assert result["status"] == "ASSESSED"
    assert row["boq_item_count"] == 2
    assert row["boq_quantity"] == 12
    assert row["boq_amount"] == 80
    assert row["duration_days"] == 3
    assert row["is_critical"] is True
    assert row["planned_resource_units"] == 12


def test_unlinked_rows_are_reported_not_guessed():
    boq, activities, resources = sample()
    boq.append({"boq_id": "B3", "quantity": 1, "unit_rate": 10})
    resources.append({"resource_id": "R2", "planned_units": 2})
    result = build_boq_schedule_resource_integration(boq, activities, resources)
    assert result["status"] == "PARTIAL"
    assert "B3" in result["unlinked_boq"]
    assert "R2" in result["unlinked_resources"]


def test_invalid_schedule_stops_integration():
    boq, activities, resources = sample()
    activities[0]["predecessors"] = ["MISSING"]
    result = build_boq_schedule_resource_integration(boq, activities, resources)
    assert result["status"] == "INVALID_SCHEDULE"


def test_rejects_negative_boq_quantity():
    boq, activities, resources = sample()
    boq[0]["quantity"] = -1
    with pytest.raises(ValueError):
        build_boq_schedule_resource_integration(boq, activities, resources)


def test_no_inputs_is_no_linked_activities():
    result = build_boq_schedule_resource_integration([], [], [])
    assert result["status"] == "NO_LINKED_ACTIVITIES"
