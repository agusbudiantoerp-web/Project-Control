import pandas as pd

from portfolio_resource_transfer import simulate_resource_transfer_impact


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


def test_transfer_conserves_capacity_and_reduces_recipient_shortfall():
    result = simulate_resource_transfer_impact(_input(), {"A": 10, "B": 90}, 50)
    assert result["available"]
    assert result["metrics"]["capacity_conserved"]
    rows = result["impact"].set_index("project_id")
    assert rows.loc["B", "scenario_unmet_per_day"] < rows.loc["B", "baseline_unmet_per_day"]
    assert rows.loc["A", "scenario_unmet_per_day"] > rows.loc["A", "baseline_unmet_per_day"]


def test_no_transfer_when_donor_release_is_zero():
    result = simulate_resource_transfer_impact(_input(), {"A": 90, "B": 10}, 0)
    assert result["transfers"].empty
    assert result["metrics"]["transferred_units"] == 0


def test_no_transfer_from_equal_or_higher_priority_project():
    result = simulate_resource_transfer_impact(_input(), {"A": 90, "B": 10}, 50)
    assert result["transfers"].empty


def test_source_data_is_not_mutated():
    source = _input()
    before = source["daily_load"].copy(deep=True)
    simulate_resource_transfer_impact(source, {"A": 90, "B": 10}, 20)
    pd.testing.assert_frame_equal(source["daily_load"], before)
