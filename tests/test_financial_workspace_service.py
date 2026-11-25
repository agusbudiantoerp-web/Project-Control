import pytest

from ai_project_control.financial_workspace_service import build_stored_project_financial_control
from ai_project_control.project_store import ProjectStore


def make_store(path):
    store = ProjectStore(path)
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "Mine Development", "currency": "IDR", "BAC": 1000,
    }])
    store.save_dataset("P1", "progress", [{
        "project_id": "P1", "activity_id": "A1", "period": "2026-10",
        "planned_value": 500, "earned_value": 400,
    }])
    store.save_dataset("P1", "actual_cost", [{
        "project_id": "P1", "period": "2026-10", "cost_code": "C1", "actual_cost": 500,
    }])
    return store


def test_financial_control_reads_persisted_project_data(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    make_store(db)
    result = build_stored_project_financial_control(db, "P1")
    assert result["project_name"] == "Mine Development"
    assert result["evm"]["SPI"] == 0.8
    assert result["evm"]["CPI"] == 0.8
    assert result["cost_forecast"]["status"] == "ASSESSED"
    assert result["source_counts"] == {"progress": 1, "actual_cost": 1}


def test_financial_control_is_project_scoped(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    make_store(db)
    with pytest.raises(ValueError, match="not found"):
        build_stored_project_financial_control(db, "P2")


def test_financial_control_rejects_explicit_currency_mismatch(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = make_store(db)
    store.save_dataset("P1", "actual_cost", [{
        "project_id": "P1", "period": "2026-11", "cost_code": "C2",
        "actual_cost": 10, "currency": "USD",
    }])
    with pytest.raises(ValueError, match="currency"):
        build_stored_project_financial_control(db, "P1")


def test_as_of_period_limits_source_records(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = make_store(db)
    store.save_dataset("P1", "progress", [{
        "project_id": "P1", "activity_id": "A2", "period": "2026-11",
        "planned_value": 500, "earned_value": 500,
    }])
    result = build_stored_project_financial_control(db, "P1", as_of_period="2026-10")
    assert result["evm"]["PV"] == 500
    assert result["source_counts"]["progress"] == 2
