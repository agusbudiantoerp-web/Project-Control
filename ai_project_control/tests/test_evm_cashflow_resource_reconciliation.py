import pandas as pd
import pytest

from core import build_cost_cashflow, calculate_evm, calculate_resource_load


def _project_inputs():
    project = pd.DataFrame([{
        "project_id": "P-CF",
        "project_name": "Cash Flow Validation",
        "planned_start": "2026-01-01",
        "planned_finish": "2026-03-31",
        "currency": "IDR",
    }])
    activities = pd.DataFrame([
        {"activity_id": "A", "wbs_id": "W1", "planned_start": "2026-01-01",
         "planned_finish": "2026-01-31", "weight_pct": 50},
        {"activity_id": "B", "wbs_id": "W1", "planned_start": "2026-02-01",
         "planned_finish": "2026-02-28", "weight_pct": 50},
    ])
    boq = pd.DataFrame([{
        "boq_id": "Q1", "wbs_id": "W1", "budget_quantity": 100,
        "unit_rate": 10, "budget_amount": 1000,
    }])
    progress = pd.DataFrame([{
        "period_end": "2026-01-31", "activity_id": "A", "boq_id": "Q1",
        "actual_quantity_to_date": 20,
    }])
    actual = pd.DataFrame([{
        "transaction_date": "2026-01-20", "amount": 100, "currency": "IDR",
    }])
    commitments = pd.DataFrame([{
        "commitment_id": "PO-1", "commitment_date": "2026-01-10",
        "committed_amount": 300, "paid_amount": 100,
        "currency": "IDR", "status": "Approved",
    }])
    return project, activities, boq, progress, actual, commitments


def test_evm_and_cashflow_reconcile_without_double_counting_paid_commitments():
    project, activities, boq, progress, actual, commitments = _project_inputs()

    evm = calculate_evm(project, activities, boq, progress, actual, "2026-01-31")
    cashflow, stats, commitment_detail = build_cost_cashflow(
        project, activities, boq, actual, commitments, "2026-01-31", progress
    )

    assert evm["BAC"] == pytest.approx(1000)
    assert evm["EV"] == pytest.approx(100)
    assert evm["AC"] == pytest.approx(100)
    assert evm["CPI"] == pytest.approx(1)
    assert stats["BAC"] == pytest.approx(evm["BAC"])
    assert stats["actual_to_date"] == pytest.approx(evm["AC"])
    assert stats["forecast_at_completion"] == pytest.approx(evm["EAC"])
    assert stats["commitment_outstanding"] == pytest.approx(200)
    assert stats["commitment_paid_reconciliation"] == pytest.approx(100)
    assert cashflow["baseline_cost"].sum() == pytest.approx(1000)
    assert cashflow["actual_cost"].sum() == pytest.approx(100)
    assert cashflow["remaining_forecast"].sum() == pytest.approx(900)
    assert commitment_detail["outstanding_amount"].sum() == pytest.approx(200)


def test_cashflow_rejects_actual_cost_currency_mismatch():
    project, activities, boq, progress, actual, commitments = _project_inputs()
    actual.loc[0, "currency"] = "USD"

    with pytest.raises(ValueError, match="currency"):
        build_cost_cashflow(
            project, activities, boq, actual, commitments, "2026-01-31", progress
        )


def test_resource_capacity_aggregates_overlapping_assignments():
    resources = pd.DataFrame([{
        "rsrc_id": "CRANE-01", "rsrc_name": "Crane", "capacity_per_day": 8,
    }])
    assignments = pd.DataFrame([
        {"task_id": "A", "rsrc_id": "CRANE-01", "target_qty": 30,
         "target_start_date": "2026-01-01", "target_end_date": "2026-01-03"},
        {"task_id": "B", "rsrc_id": "CRANE-01", "target_qty": 30,
         "target_start_date": "2026-01-01", "target_end_date": "2026-01-03"},
    ])

    summary, daily = calculate_resource_load(resources, assignments)

    assert len(daily) == 3
    assert daily["planned_load_per_day"].tolist() == pytest.approx([20, 20, 20])
    assert daily["over_capacity"].all()
    assert summary.loc[0, "overloaded_days"] == 3


def test_cashflow_rejects_activity_dates_outside_project_window():
    project, activities, boq, progress, actual, commitments = _project_inputs()
    activities.loc[0, "planned_start"] = "2025-12-31"

    with pytest.raises(ValueError, match="within project master dates"):
        build_cost_cashflow(
            project, activities, boq, actual, commitments, "2026-01-31", progress
        )


def test_cashflow_baseline_reconciles_when_activity_dates_cover_project_window():
    project, activities, boq, progress, actual, commitments = _project_inputs()
    cashflow, stats, _ = build_cost_cashflow(
        project, activities, boq, actual, commitments, "2026-01-31", progress
    )

    assert cashflow["baseline_cost"].sum() == pytest.approx(stats["BAC"])
    assert stats["BAC"] == pytest.approx(1000)


def test_change_impact_separates_approved_pending_and_rejected_changes():
    from core import calculate_change_impact

    changes = pd.DataFrame([
        {"change_id": "C1", "status": "Approved", "cost_impact": 150,
         "schedule_impact_days": 5},
        {"change_id": "C2", "status": "Pending", "cost_impact": 80,
         "schedule_impact_days": 2},
        {"change_id": "C3", "status": "Rejected", "cost_impact": 40,
         "schedule_impact_days": 1},
    ])

    detail, stats = calculate_change_impact(changes, 1000)

    assert stats["approved_cost_impact"] == pytest.approx(150)
    assert stats["approved_schedule_days"] == pytest.approx(5)
    assert stats["revised_budget"] == pytest.approx(1150)
    assert stats["pending_count"] == 1
    assert stats["pending_cost_exposure"] == pytest.approx(80)
    assert detail.loc[detail["change_id"] == "C3", "control_class"].iloc[0] == "Other / rejected"


def test_change_impact_allows_approved_cost_reduction():
    from core import calculate_change_impact

    changes = pd.DataFrame([
        {"change_id": "CR-1", "status": "Accepted", "cost_impact": -100,
         "schedule_impact_days": -3},
    ])

    _, stats = calculate_change_impact(changes, 1000)

    assert stats["approved_cost_impact"] == pytest.approx(-100)
    assert stats["approved_schedule_days"] == pytest.approx(-3)
    assert stats["revised_budget"] == pytest.approx(900)

def test_resource_load_rejects_non_finite_quantities_and_capacity():
    resources = pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":8}])
    for value in [float("inf"), float("nan"), -1]:
        assignments = pd.DataFrame([{
            "rsrc_id":"R1","target_qty":value,"target_start_date":"2026-01-01",
            "target_end_date":"2026-01-02",
        }])
        with pytest.raises(ValueError, match="target_qty must contain finite"):
            calculate_resource_load(resources, assignments)
    bad_resources = pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":float("inf")}])
    assignments = pd.DataFrame([{
        "rsrc_id":"R1","target_qty":2,"target_start_date":"2026-01-01",
        "target_end_date":"2026-01-02",
    }])
    with pytest.raises(ValueError, match="capacity_per_day must be finite"):
        calculate_resource_load(bad_resources, assignments)


def test_resource_load_rejects_blank_and_duplicate_resource_ids():
    assignments = pd.DataFrame([{"rsrc_id":" ","target_qty":1}])
    with pytest.raises(ValueError, match="non-blank rsrc_id"):
        calculate_resource_load(pd.DataFrame(), assignments)
    resources = pd.DataFrame([{"rsrc_id":"R1"},{"rsrc_id":"R1"}])
    assignments = pd.DataFrame([{"rsrc_id":"R1","target_qty":1}])
    with pytest.raises(ValueError, match="unique non-blank rsrc_id"):
        calculate_resource_load(resources, assignments)

def test_resource_load_rejects_malformed_capacity_and_extreme_date_window():
    resources = pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":"not-a-number"}])
    assignments = pd.DataFrame([{
        "rsrc_id":"R1","target_qty":2,"target_start_date":"2026-01-01",
        "target_end_date":"2026-01-02",
    }])
    with pytest.raises(ValueError, match="capacity_per_day must be finite"):
        calculate_resource_load(resources, assignments)
    resources = pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":8}])
    assignments.loc[0,"target_end_date"]="2040-01-01"
    with pytest.raises(ValueError, match="exceeds 10 years"):
        calculate_resource_load(resources, assignments)

def test_resource_load_compares_calendar_dates_not_time_of_day():
    resources = pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":8}])
    assignments = pd.DataFrame([{
        "rsrc_id":"R1","target_qty":8,
        "target_start_date":"2026-01-01 18:00:00",
        "target_end_date":"2026-01-01 06:00:00",
    }])
    summary, daily = calculate_resource_load(resources, assignments)
    assert len(daily) == 1
    assert daily.iloc[0]["planned_load_per_day"] == 8
