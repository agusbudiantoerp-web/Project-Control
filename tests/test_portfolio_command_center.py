import pytest

from ai_project_control.portfolio_command_center import build_portfolio_command_center
from ai_project_control.project_store import ProjectStore


def _save_project(store, project_id, name, spi, cpi, currency, bac):
    store.save_dataset("P0", "project_master", []) if False else None
    store.save_dataset(project_id, "project_master", [{
        "project_id": project_id, "project_name": name, "SPI": spi, "CPI": cpi,
        "currency": currency, "budget_at_completion": bac,
    }])


def test_command_center_lists_projects_and_keeps_currency_totals_separate(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    _save_project(store, "P1", "Mine A", 0.90, 0.92, "IDR", 1000)
    _save_project(store, "P2", "Road B", 1.02, 1.01, "USD", 200)
    result = build_portfolio_command_center(db)
    assert result["status"] == "ASSESSED"
    assert result["project_count"] == 2
    assert result["budget_by_currency"] == {"IDR": 1000.0, "USD": 200.0}
    assert result["projects"][0]["project_id"] == "P1"


def test_empty_database_returns_no_projects(tmp_path):
    result = build_portfolio_command_center(tmp_path / "empty.sqlite3")
    assert result["status"] == "NO_PROJECTS"
    assert result["project_count"] == 0
