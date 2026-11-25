import numpy as np
import pandas as pd
import pytest

from integrated_forecast import build_integrated_forecast


def sample_inputs():
    activities = pd.DataFrame([
        {"activity_id": "A1", "activity_name": "Preparation", "wbs_id": "1", "duration_days": 31, "predecessor_ids": "", "planned_start": "2026-01-01", "planned_finish": "2026-01-31"},
        {"activity_id": "A2", "activity_name": "Execution", "wbs_id": "1", "duration_days": 30, "predecessor_ids": "A1", "planned_start": "2026-02-01", "planned_finish": "2026-03-02"},
    ])
    boq = pd.DataFrame([
        {"boq_id": "B1", "budget_quantity": 100, "unit_rate": 1000, "budget_amount": 100000},
    ])
    progress = pd.DataFrame([
        {"boq_id": "B1", "planned_quantity_to_date": 60, "actual_quantity_to_date": 50},
    ])
    actual = pd.DataFrame([{"amount": 60000}])
    resources = pd.DataFrame([{"rsrc_id": "R1", "capacity_per_day": 8}])
    assignments = pd.DataFrame([
        {"task_id": "A1", "rsrc_id": "R1", "target_qty": 400},
    ])
    risks = pd.DataFrame([
        {"probability": 1.0, "cost_impact": 20000, "schedule_impact_days": 5},
    ])
    return activities, boq, progress, actual, resources, assignments, risks


def test_integrated_forecast_combines_cost_schedule_resources_and_risk():
    inputs = sample_inputs()
    result = build_integrated_forecast(
        *inputs, status_date="2026-02-01", simulations=1000, seed=7
    )
    assert result["bac"] == pytest.approx(100000)
    assert result["pv"] == pytest.approx(60000)
    assert result["ev"] == pytest.approx(50000)
    assert result["ac"] == pytest.approx(60000)
    assert result["cpi"] == pytest.approx(50 / 60)
    assert result["spi"] == pytest.approx(50 / 60)
    assert result["risk_cost_p80"] == pytest.approx(20000)
    assert result["risk_days_p80"] == pytest.approx(5)
    assert result["resource_overload_assignments"] == 1
    assert result["cpm_project_duration_days"] == pytest.approx(61)
    assert result["critical_activity_count"] == 2
    assert set(result["critical_activity_ids"]) == {"A1", "A2"}
    assert result["risk_adjusted_finish_p80"] >= result["forecast_finish"]


def test_integrated_forecast_is_reproducible_with_same_seed():
    inputs = sample_inputs()
    a = build_integrated_forecast(*inputs, status_date="2026-02-01", seed=123)
    b = build_integrated_forecast(*inputs, status_date="2026-02-01", seed=123)
    assert a["risk_cost_p80"] == b["risk_cost_p80"]
    assert a["risk_days_p80"] == b["risk_days_p80"]


def test_integrated_forecast_rejects_invalid_schedule_dates():
    activities = pd.DataFrame([{
        "activity_id": "A1", "planned_start": "2026-02-02",
        "planned_finish": "2026-02-01"
    }])
    with pytest.raises(ValueError, match="Tanggal"):
        build_integrated_forecast(activities)



def test_integrated_forecast_includes_reconciled_cashflow_when_project_master_is_supplied():
    activities = pd.DataFrame([
        {"activity_id": "A1", "activity_name": "Work", "wbs_id": "W1",
         "duration_days": 30, "weight_pct": 100, "predecessor_ids": "",
         "planned_start": "2026-01-01", "planned_finish": "2026-01-30"},
    ])
    project = pd.DataFrame([{
        "project_id": "P1", "project_name": "Test", "planned_start": "2026-01-01",
        "planned_finish": "2026-03-31", "currency": "IDR",
    }])
    boq = pd.DataFrame([{
        "boq_id": "B1", "wbs_id": "W1", "budget_quantity": 100,
        "unit_rate": 1000, "budget_amount": 100000,
    }])
    progress = pd.DataFrame([{
        "period_end": "2026-01-30", "activity_id": "A1", "boq_id": "B1",
        "actual_quantity_to_date": 50,
    }])
    actual = pd.DataFrame([{
        "transaction_date": "2026-01-20", "amount": 40000, "currency": "IDR",
    }])
    result = build_integrated_forecast(
        activities=activities, boq_budget=boq, progress=progress,
        actual_cost=actual, project_master=project, commitments=pd.DataFrame(),
        status_date="2026-01-30", simulations=1000,
    )
    assert result["cashflow_stats"]["BAC"] == pytest.approx(100000)
    assert result["cashflow_stats"]["actual_to_date"] == pytest.approx(40000)
    assert not result["cashflow"].empty


def test_integrated_forecast_supports_package_import_from_repository_root():
    from ai_project_control.integrated_forecast import (
        build_integrated_forecast as package_build_integrated_forecast,
    )

    activities = pd.DataFrame([
        {
            "activity_id": "A1",
            "activity_name": "Package import smoke test",
            "duration_days": 3,
            "predecessor_ids": "",
            "planned_start": "2026-01-01",
            "planned_finish": "2026-01-03",
        }
    ])
    result = package_build_integrated_forecast(
        activities, status_date="2026-01-01", simulations=100, seed=11
    )
    assert result["cpm_project_duration_days"] == pytest.approx(3)
    assert result["critical_activity_ids"] == ["A1"]
