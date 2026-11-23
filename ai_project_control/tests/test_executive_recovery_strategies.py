import pandas as pd

from executive_recovery_strategies import build_executive_recovery_strategies


def _portfolio():
    return pd.DataFrame([
        {"project_id": "P1", "project_name": "Delayed Project", "SPI": 0.75, "CPI": 0.82,
         "schedule_slip_days": 18, "BAC": 1000, "EAC": 1250, "currency": "USD"},
        {"project_id": "P2", "project_name": "Healthy Project", "SPI": 1.02, "CPI": 1.01,
         "schedule_slip_days": 0, "BAC": 500, "EAC": 500, "currency": "IDR"},
    ])


def test_generates_integrated_strategy_for_schedule_and_cost_issues():
    result = build_executive_recovery_strategies(_portfolio())
    assert result["available"]
    p1 = result["strategies"].query("project_id == 'P1'")
    assert "Integrated recovery" in p1["strategy"].tolist()
    assert "Schedule recovery" in p1["strategy"].tolist()
    assert "Cost recovery" in p1["strategy"].tolist()


def test_healthy_project_does_not_receive_false_recovery_action():
    result = build_executive_recovery_strategies(_portfolio())
    assert "P2" not in result["strategies"].get("project_id", pd.Series(dtype=str)).tolist()


def test_risk_trigger_can_create_risk_mitigation_strategy():
    risk = pd.DataFrame([{"project_id": "P2", "risk_score": 75, "risk_status": "HIGH"}])
    result = build_executive_recovery_strategies(_portfolio(), risk)
    p2 = result["strategies"].query("project_id == 'P2'")
    assert "Risk mitigation" in p2["strategy"].tolist()


def test_does_not_invent_quantified_benefits_or_mutate_source():
    source = _portfolio()
    before = source.copy(deep=True)
    result = build_executive_recovery_strategies(source)
    assert result["strategies"]["potential_benefit_not_quantified"].str.contains("Potential").all()
    pd.testing.assert_frame_equal(source, before)


def test_financial_variances_remain_project_currency_scoped():
    result = build_executive_recovery_strategies(_portfolio())
    rows = result["strategies"].query("category == 'Cost'")
    assert set(rows["currency"]) == {"USD"}
