import pytest

from ai_project_control.portfolio_cashflow_intelligence import build_portfolio_cashflow_view


def test_portfolio_cost_totals_are_grouped_by_currency():
    result = build_portfolio_cashflow_view([
        {"project_id": "P1", "project_name": "Mine A", "currency": "IDR", "budget": 1000, "actual_cost": 700},
        {"project_id": "P2", "project_name": "Road B", "currency": "IDR", "budget": 500, "actual_cost": 600},
        {"project_id": "P3", "project_name": "Plant C", "currency": "USD", "budget": 200, "actual_cost": 100},
    ])
    assert result["totals_by_currency"]["IDR"] == {
        "budget": 1500.0, "actual_cost": 1300.0, "remaining_budget": 200.0
    }
    assert result["totals_by_currency"]["USD"]["remaining_budget"] == 100
    assert result["projects_over_budget"] == 1
    assert result["projects"][1]["status"] == "OVER_BUDGET"


def test_missing_or_invalid_finance_is_unassessed_not_zero():
    result = build_portfolio_cashflow_view([
        {"project_id": "P1", "currency": "IDR", "budget": None, "actual_cost": 100},
        {"project_id": "P2", "currency": "", "budget": 100, "actual_cost": 50},
        {"project_id": "P3", "currency": "USD", "budget": -1, "actual_cost": 5},
    ])
    assert result["project_count_assessed"] == 0
    assert result["project_count_unassessed"] == 3
    assert result["totals_by_currency"] == {}


def test_zero_budget_has_no_division_by_zero():
    result = build_portfolio_cashflow_view([
        {"project_id": "P1", "currency": "IDR", "budget": 0, "actual_cost": 0}
    ])
    assert result["projects"][0]["cost_utilization_pct"] is None


def test_duplicate_projects_and_bad_input_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        build_portfolio_cashflow_view([
            {"project_id": "P1", "currency": "IDR", "budget": 10, "actual_cost": 5},
            {"project_id": "P1", "currency": "IDR", "budget": 20, "actual_cost": 5},
        ])
    with pytest.raises(TypeError):
        build_portfolio_cashflow_view({})
