"""Regression tests for the deterministic portfolio performance scorecard."""
from ai_project_control.portfolio_performance import build_portfolio_scorecard, score_project


def test_missing_core_metrics_are_not_scored_as_safe():
    row = score_project({"project_id": "P-1", "SPI": 1.05})
    assert row["status"] == "INSUFFICIENT_DATA"
    assert row["performance_score"] is None
    assert row["data_gaps"] == ["CPI"]


def test_equal_weight_score_and_states():
    row = score_project({"project_id": "P-2", "SPI": 1.2, "CPI": 0.9})
    assert row["status"] == "ASSESSED"
    assert row["performance_score"] == 87.5
    assert row["schedule_state"] == "GREEN"
    assert row["cost_state"] == "RED"


def test_non_finite_metrics_are_treated_as_missing():
    row = score_project({"project_id": "P-3", "SPI": float("nan"), "CPI": float("inf")})
    assert row["status"] == "INSUFFICIENT_DATA"
    assert set(row["data_gaps"]) == {"SPI", "CPI"}


def test_budget_totals_are_separated_by_currency():
    result = build_portfolio_scorecard([
        {"project_id": "A", "SPI": 1, "CPI": 1, "budget_at_completion": 100, "currency": "IDR"},
        {"project_id": "B", "SPI": 1, "CPI": 1, "budget_at_completion": 20, "currency": "USD"},
        {"project_id": "C", "SPI": 0.8, "CPI": 0.9, "budget_at_completion": 50, "currency": "IDR"},
    ])
    assert result["summary"]["budget_by_currency"] == {"IDR": 150.0, "USD": 20.0}


def test_ranked_list_excludes_unassessed_projects():
    result = build_portfolio_scorecard([
        {"project_id": "A", "SPI": 0.8, "CPI": 0.9},
        {"project_id": "B", "SPI": 1.1, "CPI": 1.1},
        {"project_id": "C", "SPI": None, "CPI": 1.0},
    ])
    assert result["ranked_project_ids"] == ["A", "B"]
    assert result["summary"]["insufficient_data_count"] == 1


def test_risk_score_breaks_equal_performance_ties():
    result = build_portfolio_scorecard([
        {"project_id": "A", "SPI": 0.9, "CPI": 0.9, "risk_score": 20},
        {"project_id": "B", "SPI": 0.9, "CPI": 0.9, "risk_score": 80},
    ])
    assert result["ranked_project_ids"] == ["B", "A"]
