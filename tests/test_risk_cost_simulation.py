import pytest
from ai_project_control.risk_cost_simulation import build_risk_cost_simulation


def risks():
    return [
        {"risk_id": "R1", "probability": 0.5, "cost_impact_min": 100,
         "cost_impact_most_likely": 200, "cost_impact_max": 300,
         "risk_type": "THREAT", "currency": "IDR", "activity_id": "A1", "wbs_id": "W1"},
        {"risk_id": "R2", "probability": 0.2, "cost_impact_min": 50,
         "cost_impact_most_likely": 100, "cost_impact_max": 150,
         "risk_type": "OPPORTUNITY", "currency": "IDR"},
    ]


def test_monte_carlo_is_reproducible_and_reports_percentiles():
    result = build_risk_cost_simulation(risks(), 1000, "IDR", iterations=2000, seed=7)
    again = build_risk_cost_simulation(risks(), 1000, "IDR", iterations=2000, seed=7)
    assert result == again
    assert result["status"] == "ASSESSED"
    assert result["risk_register"][0]["activity_id"] == "A1"
    assert result["risk_register"][0]["wbs_id"] == "W1"
    assert result["p50_cost"] >= 0
    assert result["p80_cost"] >= result["p50_cost"]
    assert result["p90_cost"] >= result["p80_cost"]
    assert result["p80_contingency"] == max(0, result["p80_cost"] - 1000)


def test_empty_risk_register_is_not_zero_risk():
    result = build_risk_cost_simulation([], 1000, "IDR")
    assert result["status"] == "NO_RISKS"
    assert "not evidence" in result["message"]


def test_currency_mismatch_is_rejected():
    data = risks()
    data[0]["currency"] = "USD"
    with pytest.raises(ValueError, match="currency"):
        build_risk_cost_simulation(data, 1000, "IDR")


def test_invalid_probability_and_impact_order_are_rejected():
    data = risks()
    data[0]["probability"] = 1.5
    with pytest.raises(ValueError, match="probability"):
        build_risk_cost_simulation(data, 1000, "IDR")
    data = risks()
    data[0]["cost_impact_min"] = 250
    with pytest.raises(ValueError, match="impacts"):
        build_risk_cost_simulation(data, 1000, "IDR")


def test_opportunity_can_reduce_simulated_cost_but_not_below_zero():
    data = [{"risk_id": "O1", "probability": 1, "cost_impact_min": 50,
             "cost_impact_most_likely": 50, "cost_impact_max": 50,
             "risk_type": "OPPORTUNITY"}]
    result = build_risk_cost_simulation(data, 100, "IDR", iterations=1000)
    assert result["p50_cost"] == 50


def test_missing_currency_is_not_assumed():
    result = build_risk_cost_simulation(risks(), 1000, "")
    assert result["status"] == "INSUFFICIENT_DATA"


def test_triangular_expected_impact_uses_distribution_mean_for_ranking():
    data = [
        {"risk_id": "WIDE", "probability": 1, "cost_impact_min": 0,
         "cost_impact_most_likely": 10, "cost_impact_max": 100,
         "risk_type": "THREAT", "currency": "IDR"},
        {"risk_id": "NARROW", "probability": 1, "cost_impact_min": 30,
         "cost_impact_most_likely": 30, "cost_impact_max": 30,
         "risk_type": "THREAT", "currency": "IDR"},
    ]
    result = build_risk_cost_simulation(data, 1000, "IDR", iterations=1000)
    ranked = {row["risk_id"]: row["expected_cost_impact"] for row in result["risk_register"]}
    assert ranked["WIDE"] == pytest.approx(110 / 3, abs=0.01)
    assert ranked["NARROW"] == 30
    assert result["risk_register"][0]["risk_id"] == "WIDE"


def test_risk_cost_simulation_rejects_boolean_probability_and_base_cost():
    data = risks()
    data[0]["probability"] = True
    with pytest.raises(ValueError, match="not boolean"):
        build_risk_cost_simulation(data, 1000, "IDR", iterations=1000)
    with pytest.raises(ValueError, match="not boolean"):
        build_risk_cost_simulation(risks(), True, "IDR", iterations=1000)
