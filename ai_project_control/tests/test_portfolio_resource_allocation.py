import pandas as pd

from portfolio_resource_allocation import build_resource_allocation_scenario


def _summary():
    details = pd.DataFrame([
        {"project_id": "P1", "rsrc_id": "EX1", "shared_resource_id": "EX-01",
         "capacity_per_day": 5, "resource_name": "Excavator"},
        {"project_id": "P2", "rsrc_id": "EX2", "shared_resource_id": "EX-01",
         "capacity_per_day": 5, "resource_name": "Excavator"},
    ])
    daily = pd.DataFrame([
        {"project_id": "P1", "rsrc_id": "EX1", "date": "2026-11-24", "demand_per_day": 4},
        {"project_id": "P2", "rsrc_id": "EX2", "date": "2026-11-24", "demand_per_day": 4},
    ])
    return {"resources": details, "daily_load": daily}


def test_priority_receives_capacity_first_and_reduces_unmet_demand():
    result = build_resource_allocation_scenario(_summary(), {"P1": 10, "P2": 5})
    assert result["available"]
    rows = result["allocations"].set_index("project_id")
    assert rows.loc["P1", "allocated_per_day"] == 4
    assert rows.loc["P1", "unmet_demand_per_day"] == 0
    assert rows.loc["P2", "allocated_per_day"] == 1
    assert rows.loc["P2", "unmet_demand_per_day"] == 3


def test_equal_priority_uses_stable_project_id_order():
    result = build_resource_allocation_scenario(_summary(), {"P1": 1, "P2": 1})
    rows = result["allocations"].set_index("project_id")
    assert rows.loc["P1", "allocated_per_day"] == 4
    assert rows.loc["P2", "allocated_per_day"] == 1


def test_unshared_resource_returns_unavailable_without_guessing():
    source = _summary()
    source["resources"]["shared_resource_id"] = ""
    result = build_resource_allocation_scenario(source)
    assert not result["available"]
    assert result["allocations"].empty


def test_source_daily_load_is_not_mutated():
    source = _summary()
    before = source["daily_load"].copy(deep=True)
    build_resource_allocation_scenario(source, {"P1": 2})
    pd.testing.assert_frame_equal(source["daily_load"], before)
