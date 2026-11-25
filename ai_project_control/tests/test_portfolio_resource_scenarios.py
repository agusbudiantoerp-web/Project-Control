import pandas as pd

from portfolio_resource_scenarios import compare_resource_allocation_scenarios


def _input():
    return {
        "resources": pd.DataFrame([
            {"project_id": "A", "rsrc_id": "R1", "shared_resource_id": "CRANE-1",
             "capacity_per_day": 10, "resource_name": "Crane"},
            {"project_id": "B", "rsrc_id": "R2", "shared_resource_id": "CRANE-1",
             "capacity_per_day": 10, "resource_name": "Crane"},
        ]),
        "daily_load": pd.DataFrame([
            {"project_id": "A", "rsrc_id": "R1", "date": "2026-11-24", "demand_per_day": 8},
            {"project_id": "B", "rsrc_id": "R2", "date": "2026-11-24", "demand_per_day": 8},
        ]),
    }


def test_all_policies_respect_shared_capacity():
    result = compare_resource_allocation_scenarios(_input(), {"A": 90, "B": 10})
    assert result["available"]
    totals = result["allocations"].groupby(["scenario", "date"])["allocated_per_day"].sum()
    assert (totals <= 10 + 1e-9).all()


def test_priority_first_favors_higher_risk_project():
    result = compare_resource_allocation_scenarios(_input(), {"A": 90, "B": 10})
    rows = result["allocations"]
    rows = rows[rows["scenario"] == "Priority first"].set_index("project_id")
    assert rows.loc["A", "allocated_per_day"] == 8
    assert rows.loc["B", "allocated_per_day"] == 2


def test_equal_share_is_proportional_and_fair():
    result = compare_resource_allocation_scenarios(_input(), {"A": 90, "B": 10})
    rows = result["allocations"]
    rows = rows[rows["scenario"] == "Equal fair share"].set_index("project_id")
    assert rows.loc["A", "allocated_per_day"] == 5
    assert rows.loc["B", "allocated_per_day"] == 5


def test_source_data_is_not_mutated():
    source = _input()
    before = source["daily_load"].copy(deep=True)
    compare_resource_allocation_scenarios(source, {"A": 50})
    pd.testing.assert_frame_equal(source["daily_load"], before)
