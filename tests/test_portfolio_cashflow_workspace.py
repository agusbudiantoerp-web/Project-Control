from ai_project_control.portfolio_cashflow_workspace import build_stored_portfolio_cashflow_view
from ai_project_control.project_store import ProjectStore


def _project(store, project_id="P1", *, bac=None, currency="IDR"):
    master = {"project_id": project_id, "project_name": project_id, "currency": currency}
    if bac is not None:
        master["BAC"] = bac
    store.save_dataset(project_id, "project_master", [master])


def test_missing_actual_cost_is_unassessed_not_zero(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    _project(store, bac=1000)
    store.save_dataset("P1", "actual_cost", [{
        "project_id": "P1", "period": "2026-11", "cost_code": "C1",
        "actual_cost": None,
    }])
    result = build_stored_portfolio_cashflow_view(db)
    assert result["project_count_assessed"] == 0
    assert result["unassessed_projects"][0]["project_id"] == "P1"


def test_missing_boq_amount_is_unassessed_not_zero(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    _project(store)
    store.save_dataset("P1", "boq", [{
        "project_id": "P1", "boq_id": "B1", "description": "Work package",
        "amount": None,
    }])
    store.save_dataset("P1", "actual_cost", [{
        "project_id": "P1", "period": "2026-11", "cost_code": "C1",
        "actual_cost": 100,
    }])
    result = build_stored_portfolio_cashflow_view(db)
    assert result["project_count_assessed"] == 0
    assert result["unassessed_projects"][0]["project_id"] == "P1"


def test_mixed_currency_actual_cost_is_not_aggregated(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    _project(store, bac=1000, currency="IDR")
    store.save_dataset("P1", "actual_cost", [{
        "project_id": "P1", "period": "2026-11", "cost_code": "C1",
        "actual_cost": 100, "currency": "USD",
    }])
    result = build_stored_portfolio_cashflow_view(db)
    assert result["project_count_assessed"] == 0
    assert result["unassessed_projects"][0]["project_id"] == "P1"


def test_complete_zero_actual_cost_is_valid_evidence(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    _project(store, bac=1000)
    store.save_dataset("P1", "actual_cost", [{
        "project_id": "P1", "period": "2026-11", "cost_code": "C1",
        "actual_cost": 0,
    }])
    result = build_stored_portfolio_cashflow_view(db)
    assert result["project_count_assessed"] == 1
    assert result["projects"][0]["actual_cost"] == 0
