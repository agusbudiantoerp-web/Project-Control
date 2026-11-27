import pytest

from ai_project_control.recovery_effectiveness import evaluate_recovery_effectiveness


def test_positive_recovery_indicators_and_cost_within_budget():
    result = evaluate_recovery_effectiveness(
        {"SPI": .80, "CPI": .90, "risk_score": 80, "delayed_activity_count": 5},
        {"SPI": .95, "CPI": .98, "risk_score": 55, "delayed_activity_count": 2},
        approved_recovery_budget=100, actual_recovery_cost=85, currency="IDR",
    )
    assert result["status"] == "POSITIVE_INDICATORS"
    assert result["indicator_summary"]["improved"] == 4
    assert result["recovery_cost"]["status"] == "WITHIN_BUDGET"
    assert result["recovery_cost"]["variance_favourable"] == 15


def test_mixed_result_does_not_hide_worsening_indicator():
    result = evaluate_recovery_effectiveness(
        {"SPI": .8, "CPI": .9}, {"SPI": .95, "CPI": .82}
    )
    assert result["status"] == "MIXED_INDICATORS"
    assert result["comparisons"]["SPI"]["status"] == "IMPROVED"
    assert result["comparisons"]["CPI"]["status"] == "WORSENED"


def test_missing_and_invalid_metrics_are_unassessed():
    result = evaluate_recovery_effectiveness(
        {"SPI": None, "CPI": "bad"}, {"SPI": .9, "CPI": .9}
    )
    assert result["indicator_summary"]["unassessed"] == 2


def test_all_metrics_missing_returns_insufficient_data():
    assert evaluate_recovery_effectiveness({}, {})["status"] == "INSUFFICIENT_DATA"


def test_cost_overrun_is_reported_separately():
    result = evaluate_recovery_effectiveness(
        {"SPI": .8}, {"SPI": .9},
        approved_recovery_budget=1000, actual_recovery_cost=1200,
    )
    assert result["recovery_cost"]["status"] == "OVER_BUDGET"
    assert result["recovery_cost"]["variance_favourable"] == -200


@pytest.mark.parametrize("budget,cost", [(-1, 0), (100, -1)])
def test_negative_cost_values_rejected(budget, cost):
    with pytest.raises(ValueError):
        evaluate_recovery_effectiveness({}, {}, approved_recovery_budget=budget, actual_recovery_cost=cost)


def test_rejects_non_mapping_snapshots():
    with pytest.raises(TypeError):
        evaluate_recovery_effectiveness([], {})
