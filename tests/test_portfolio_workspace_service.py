from ai_project_control.portfolio_workspace_service import build_saved_portfolio_report
from ai_project_control.project_store import ProjectStore


def add_project(store, project_id, name, pv, ev, ac, currency="IDR"):
    store.save_dataset(project_id, "project_master", [{
        "project_id": project_id, "project_name": name, "currency": currency, "BAC": 1000,
    }])
    if pv is not None:
        store.save_dataset(project_id, "progress", [{
            "project_id": project_id, "activity_id": "A1", "period": "2026-10",
            "planned_value": pv, "earned_value": ev,
        }])
    if ac is not None:
        store.save_dataset(project_id, "actual_cost", [{
            "project_id": project_id, "period": "2026-10",
            "cost_code": "C1", "actual_cost": ac,
        }])


def test_saved_portfolio_discovers_projects_and_scores_them(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", 500, 400, 500)
    add_project(store, "P2", "Project Two", 500, 500, 400)
    result = build_saved_portfolio_report(db, as_of_period="2026-10")
    assert result["project_count"] == 2
    assert result["scorecard"]["summary"]["assessed_count"] == 2
    assert result["scorecard"]["summary"]["budget_by_currency"] == {"IDR": 2000}
    assert "Project One" in result["executive_report"]


def test_saved_portfolio_marks_missing_data_unassessed(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", None, None, None)
    result = build_saved_portfolio_report(db)
    assert result["scorecard"]["summary"]["insufficient_data_count"] == 1
    assert result["scorecard"]["projects"][0]["status"] == "INSUFFICIENT_DATA"


def test_saved_portfolio_does_not_combine_currencies(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project IDR", 500, 400, 500, "IDR")
    add_project(store, "P2", "Project USD", 500, 450, 450, "USD")
    result = build_saved_portfolio_report(db)
    assert result["scorecard"]["summary"]["budget_by_currency"] == {"IDR": 1000, "USD": 1000}


def test_saved_portfolio_empty_workspace_is_valid_empty_result(tmp_path):
    result = build_saved_portfolio_report(tmp_path / "empty.sqlite3")
    assert result["project_count"] == 0
    assert result["scorecard"]["summary"]["project_count"] == 0
