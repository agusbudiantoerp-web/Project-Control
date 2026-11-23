import pandas as pd

from portfolio_resource_intelligence import build_portfolio_resource_summary


def _project(project_id, capacity=5, resource_id="R1", quantity=20):
    return {
        "project_id": project_id,
        "project_name": f"Project {project_id}",
        "resources": pd.DataFrame([{
            "rsrc_id": resource_id, "rsrc_name": "Crew", "rsrc_type": "Labor",
            "capacity_per_day": capacity,
        }]),
        "assignments": pd.DataFrame([{
            "rsrc_id": resource_id, "target_qty": quantity,
            "target_start_date": "2026-01-01", "target_end_date": "2026-01-04",
        }]),
    }


def test_portfolio_resource_summary_detects_overload_and_daily_loading():
    result = build_portfolio_resource_summary([_project("P1", capacity=4, quantity=24)])
    assert result["available"]
    row = result["resources"].iloc[0]
    assert row["peak_demand_per_day"] == 6
    assert row["overloaded_days"] == 4
    assert result["daily_load"]["over_capacity"].all()


def test_same_resource_id_is_not_merged_across_projects():
    result = build_portfolio_resource_summary([
        _project("P1", capacity=5, quantity=20),
        _project("P2", capacity=10, quantity=20),
    ])
    assert len(result["resources"]) == 2
    assert set(result["resources"]["project_id"]) == {"P1", "P2"}
    assert result["project_summary"]["resources_tracked"].sum() == 2


def test_portfolio_resource_summary_handles_missing_datasets():
    result = build_portfolio_resource_summary([{
        "project_id": "P1", "resources": pd.DataFrame(), "assignments": pd.DataFrame()
    }])
    assert not result["available"]
    assert result["resources"].empty
