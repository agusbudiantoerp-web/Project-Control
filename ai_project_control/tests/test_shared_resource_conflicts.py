import pandas as pd

from portfolio_resource_intelligence import (
    build_portfolio_resource_summary,
    detect_shared_resource_conflicts,
)


def _project(project_id, qty, capacity, shared_id="EXC-01"):
    return {
        "project_id": project_id,
        "project_name": project_id,
        "resources": pd.DataFrame([{
            "rsrc_id": "EXC", "rsrc_name": "Excavator",
            "rsrc_type": "Equipment", "capacity_per_day": capacity,
            "shared_resource_id": shared_id,
        }]),
        "assignments": pd.DataFrame([{
            "rsrc_id": "EXC", "target_qty": qty,
            "target_start_date": "2026-01-01",
            "target_end_date": "2026-01-04",
        }]),
    }


def test_shared_resource_detects_cross_project_capacity_conflict():
    portfolio = build_portfolio_resource_summary([
        _project("P1", qty=16, capacity=5),
        _project("P2", qty=16, capacity=5),
    ])
    result = detect_shared_resource_conflicts(portfolio)
    assert result["available"]
    assert result["summary"].iloc[0]["overloaded_days"] == 4
    assert result["daily_conflicts"]["project_count"].eq(2).all()
    assert result["daily_conflicts"]["over_capacity"].all()


def test_resource_without_shared_identity_is_not_merged():
    portfolio = build_portfolio_resource_summary([
        _project("P1", qty=16, capacity=5, shared_id=""),
        _project("P2", qty=16, capacity=5, shared_id=""),
    ])
    result = detect_shared_resource_conflicts(portfolio)
    assert not result["available"]


def test_shared_capacity_mismatch_is_flagged():
    portfolio = build_portfolio_resource_summary([
        _project("P1", qty=8, capacity=5),
        _project("P2", qty=8, capacity=7),
    ])
    result = detect_shared_resource_conflicts(portfolio)
    assert result["available"]
    assert result["summary"].iloc[0]["capacity_mismatch"]
    assert result["summary"].iloc[0]["allocation_status"] == "Capacity mismatch - verify"
