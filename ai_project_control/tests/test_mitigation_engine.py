import pandas as pd
import pytest

from mitigation_engine import build_mitigation_advice, compare_recovery_scenarios


def schedule():
    return pd.DataFrame([
        {"activity_id":"A1","activity_name":"Mobilization","wbs_id":"1","duration_days":5,"predecessor_ids":"","planned_start":"2026-01-01","planned_finish":"2026-01-05"},
        {"activity_id":"A2","activity_name":"Construction","wbs_id":"1","duration_days":10,"predecessor_ids":"A1","planned_start":"2026-01-06","planned_finish":"2026-01-15"},
    ])


def test_advisor_returns_critical_path_actions():
    evm={"SPI":0.8,"CPI":0.9}
    risks=pd.DataFrame([{"probability":0.5,"cost_impact":100000,"schedule_impact_days":8}])
    resources=pd.DataFrame([{"rsrc_id":"R1","peak_utilization_pct":125}])
    result=build_mitigation_advice(schedule(),evm,risks,resources)
    assert result["critical_activity_ids"] == ["A1","A2"]
    assert len(result["actions"]) >= 4
    assert result["actions"]["recommended_action"].notna().all()


def test_advisor_handles_missing_performance_data():
    result=build_mitigation_advice(schedule())
    assert not result["actions"].empty


def test_recovery_scenario_does_not_invent_crash_cost():
    result=compare_recovery_scenarios(schedule(),5)
    assert result["scenario_available"] is False
    assert pd.isna(result["incremental_crash_cost"])



def test_advisor_reads_resource_engine_capacity_column():
    resources = pd.DataFrame([{"rsrc_id":"R1","peak_capacity_utilization_pct":135}])
    result = build_mitigation_advice(schedule(), resource_summary=resources)
    assert result["actions"]["finding"].str.contains("exceed 100% capacity").any()



def test_recovery_scenario_uses_achieved_duration_and_crash_cost():
    activities = schedule().copy()
    activities["crash_duration_days"] = [2, 8]
    activities["crash_cost_per_day"] = [100, 200]
    result = compare_recovery_scenarios(activities, 5)
    assert result["scenario_available"] is True
    assert result["scenario_duration_days"] == pytest.approx(10)
    assert result["days_saved"] == pytest.approx(5)
    assert result["incremental_crash_cost"] == pytest.approx(700)
    assert result["cost_per_day_saved"] == pytest.approx(140)
    assert not result["crash_detail"].empty


def test_recovery_scenario_reports_infeasible_target_without_raising():
    activities = schedule().copy()
    activities["crash_duration_days"] = [5, 10]
    activities["crash_cost_per_day"] = [100, 200]
    result = compare_recovery_scenarios(activities, 5)
    assert result["scenario_available"] is False
    assert "infeasible" in result["note"].lower()


def test_recovery_scenario_rejects_crash_duration_longer_than_normal():
    activities = schedule().copy()
    activities["crash_duration_days"] = [6, 8]
    activities["crash_cost_per_day"] = [100, 200]
    result = compare_recovery_scenarios(activities, 1)
    assert result["scenario_available"] is False
    assert "invalid" in result["note"].lower() or "exceeds" in result["note"].lower()
