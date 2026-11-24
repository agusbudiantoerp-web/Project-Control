import pytest

from ai_project_control.portfolio_risk_resource_intelligence import build_portfolio_risk_resource_view


def test_portfolio_risks_are_grouped_by_currency_and_ranked():
    result = build_portfolio_risk_resource_view(
        [
            {"project_id": "P1", "risk_id": "R1", "probability": .5, "impact": 100, "currency": "IDR"},
            {"project_id": "P2", "risk_id": "R2", "probability": .2, "impact": 100, "currency": "USD"},
        ],
        [],
    )
    assert result["risk_count_assessed"] == 2
    assert result["expected_exposure_by_currency"] == {"IDR": 50.0, "USD": 20.0}
    assert result["top_risks"][0]["risk_id"] == "R1"


def test_shared_resource_overload_only_when_capacity_and_units_match():
    result = build_portfolio_risk_resource_view(
        [],
        [
            {"project_id": "P1", "resource_id": "EX-01", "period": "2026-12", "unit": "hours", "planned_units": 70, "capacity_units": 100},
            {"project_id": "P2", "resource_id": "EX-01", "period": "2026-12", "unit": "hours", "planned_units": 50, "capacity_units": 100},
            {"project_id": "P3", "resource_id": "EX-02", "period": "2026-12", "unit": "hours", "planned_units": 90, "capacity_units": 100},
        ],
    )
    assert result["shared_resource_period_count"] == 1
    assert result["shared_resource_conflict_count"] == 1
    conflict = result["shared_resource_conflicts"][0]
    assert conflict["total_planned_demand"] == 120
    assert conflict["overload_units"] == 20
    assert conflict["projects"] == ["P1", "P2"]


def test_conflicting_capacity_is_unassessed_not_called_overload():
    result = build_portfolio_risk_resource_view(
        [],
        [
            {"project_id": "P1", "resource_id": "R", "period": "W1", "unit": "shift", "planned_units": 7, "capacity_units": 10},
            {"project_id": "P2", "resource_id": "R", "period": "W1", "unit": "shift", "planned_units": 8, "capacity_units": 12},
        ],
    )
    assert result["shared_resource_conflict_count"] == 0
    assert any("capacity declarations conflict" in row["reason"] for row in result["unassessed_resources"])


def test_invalid_risk_data_is_reported_and_duplicate_keys_rejected():
    result = build_portfolio_risk_resource_view(
        [{"project_id": "P1", "risk_id": "R1", "probability": 1.2, "impact": 5, "currency": "IDR"}],
        [],
    )
    assert result["risk_count_unassessed"] == 1
    with pytest.raises(ValueError, match="duplicate risk"):
        build_portfolio_risk_resource_view(
            [
                {"project_id": "P1", "risk_id": "R1", "probability": .5, "impact": 5, "currency": "IDR"},
                {"project_id": "P1", "risk_id": "R1", "probability": .5, "impact": 5, "currency": "IDR"},
            ], [],
        )


def test_risk_impact_falls_back_when_optional_most_likely_is_null():
    result = build_portfolio_risk_resource_view(
        [{
            "project_id": "P1", "risk_id": "R1", "probability": .5,
            "cost_impact_most_likely": None, "impact": 40, "currency": "IDR",
        }],
        [],
    )
    assert result["risk_count_assessed"] == 1
    assert result["top_risks"][0]["expected_exposure"] == 20


def test_empty_portfolio_is_insufficient_data():
    result = build_portfolio_risk_resource_view([], [])
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["expected_exposure_by_currency"] == {}
