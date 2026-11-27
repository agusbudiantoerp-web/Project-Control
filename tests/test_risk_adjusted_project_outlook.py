import pytest

from ai_project_control.risk_adjusted_project_outlook import build_risk_adjusted_project_outlook


def sample_activities():
    return [
        {"activity_id": "A1", "predecessors": [], "duration_min_days": 4,
         "duration_most_likely_days": 5, "duration_max_days": 6},
        {"activity_id": "A2", "predecessors": ["A1"], "duration_min_days": 2,
         "duration_most_likely_days": 3, "duration_max_days": 4},
    ]


def sample_cost_risks():
    return [
        {"risk_id": "C1", "probability": 0.8, "cost_impact_min": 10,
         "cost_impact_most_likely": 20, "cost_impact_max": 30,
         "risk_type": "THREAT", "currency": "IDR"}
    ]


def sample_schedule_risks():
    return [
        {"risk_id": "S1", "activity_id": "A2", "probability": 0.8,
         "delay_min_days": 1, "delay_most_likely_days": 2, "delay_max_days": 3}
    ]


def test_combined_outlook_reports_marginal_cost_and_schedule_percentiles():
    result = build_risk_adjusted_project_outlook(
        base_cost=1000, currency="IDR", cost_risks=sample_cost_risks(),
        activities=sample_activities(), schedule_risks=sample_schedule_risks(),
        project_start_date="2026-11-01", iterations=1000, seed=11,
    )
    assert result["status"] == "ASSESSED"
    summary = result["executive_summary"]
    assert summary["cost_p50"] <= summary["cost_p80"] <= summary["cost_p90"]
    assert summary["finish_p50"] <= summary["finish_p80"] <= summary["finish_p90"]
    assert summary["p80_contingency"] >= 0
    assert any("separate marginal" in item for item in result["interpretation"])


def test_combined_outlook_is_reproducible():
    args = dict(
        base_cost=1000, currency="IDR", cost_risks=sample_cost_risks(),
        activities=sample_activities(), schedule_risks=sample_schedule_risks(),
        project_start_date="2026-11-01", iterations=1000, seed=9,
    )
    assert build_risk_adjusted_project_outlook(**args) == build_risk_adjusted_project_outlook(**args)


def test_missing_schedule_does_not_claim_full_assessment():
    result = build_risk_adjusted_project_outlook(
        base_cost=1000, currency="IDR", cost_risks=sample_cost_risks(),
        activities=[], schedule_risks=[], project_start_date="2026-11-01",
        iterations=1000,
    )
    assert result["status"] == "PARTIALLY_ASSESSED"
    assert result["schedule_outlook"]["status"] == "NO_ACTIVITIES"


def test_invalid_schedule_risk_is_rejected():
    bad_risk = [{"risk_id": "S1", "activity_id": "UNKNOWN", "probability": 0.5,
                 "delay_min_days": 1, "delay_most_likely_days": 2, "delay_max_days": 3}]
    with pytest.raises(ValueError, match="known activity"):
        build_risk_adjusted_project_outlook(
            base_cost=1000, currency="IDR", cost_risks=sample_cost_risks(),
            activities=sample_activities(), schedule_risks=bad_risk,
            project_start_date="2026-11-01", iterations=1000,
        )
