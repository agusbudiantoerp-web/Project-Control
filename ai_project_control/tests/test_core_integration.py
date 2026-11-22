import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from core import calculate_cpm, calculate_evm, risk_analysis, validate_dataset


def test_cpm_forward_backward_pass_and_critical_path():
    activities = pd.DataFrame([
        {"activity_id": "A", "activity_name": "A", "wbs_id": "1", "duration_days": 5, "predecessor_ids": ""},
        {"activity_id": "B", "activity_name": "B", "wbs_id": "1", "duration_days": 3, "predecessor_ids": "A"},
        {"activity_id": "C", "activity_name": "C", "wbs_id": "1", "duration_days": 2, "predecessor_ids": "A"},
        {"activity_id": "D", "activity_name": "D", "wbs_id": "1", "duration_days": 4, "predecessor_ids": "B,C"},
    ])
    result, stats = calculate_cpm(activities)
    rows = result.set_index("activity_id")
    assert stats["project_duration"] == 12
    assert bool(rows.loc["A", "is_critical"])
    assert bool(rows.loc["B", "is_critical"])
    assert not bool(rows.loc["C", "is_critical"])
    assert bool(rows.loc["D", "is_critical"])
    assert rows.loc["C", "total_float_days"] == 1


def test_cpm_rejects_unknown_predecessor_and_cycle():
    bad = pd.DataFrame([
        {"activity_id": "A", "activity_name": "A", "wbs_id": "1", "duration_days": 1, "predecessor_ids": "MISSING"}
    ])
    try:
        calculate_cpm(bad)
    except ValueError as exc:
        assert "unknown predecessor" in str(exc)
    else:
        raise AssertionError("Unknown predecessor must fail validation")

    cycle = pd.DataFrame([
        {"activity_id": "A", "activity_name": "A", "wbs_id": "1", "duration_days": 1, "predecessor_ids": "B"},
        {"activity_id": "B", "activity_name": "B", "wbs_id": "1", "duration_days": 1, "predecessor_ids": "A"},
    ])
    try:
        calculate_cpm(cycle)
    except ValueError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("Precedence cycle must fail validation")


def test_activity_business_validation_checks_wbs_and_dates():
    activities = pd.DataFrame([{
        "activity_id": "A1", "wbs_id": "UNKNOWN", "activity_name": "Work",
        "duration_days": 2, "planned_start": "2026-02-10",
        "planned_finish": "2026-02-09", "predecessor_ids": "",
        "weight_pct": 100,
    }])
    issues = validate_dataset("activities.csv", activities, {
        "wbs.csv": pd.DataFrame([{"wbs_id": "1.1"}])
    })
    joined = " ".join(issues)
    assert "WBS tidak ditemukan" in joined
    assert "planned_finish" in joined


def test_evm_known_case():
    activities = pd.DataFrame([{
        "activity_id": "A1", "wbs_id": "1.1", "activity_name": "Work",
        "duration_days": 10, "planned_start": "2026-01-01",
        "planned_finish": "2026-01-10", "predecessor_ids": "",
        "weight_pct": 100,
    }])
    boq = pd.DataFrame([{
        "boq_id": "B1", "wbs_id": "1.1", "description": "Work",
        "unit": "m3", "budget_quantity": 100, "unit_rate": 10,
        "budget_amount": 1000,
    }])
    progress = pd.DataFrame([{
        "period_end": "2026-01-05", "activity_id": "A1", "boq_id": "B1",
        "planned_quantity_to_date": 50, "actual_quantity_to_date": 40,
    }])
    actual = pd.DataFrame([{"transaction_date": "2026-01-05", "amount": 300}])
    result = calculate_evm(pd.DataFrame(), activities, boq, progress, actual, "2026-01-05")
    assert result["BAC"] == 1000
    assert result["PV"] == 500
    assert result["EV"] == 400
    assert result["AC"] == 300
    assert result["SPI"] == 0.8
    assert np.isclose(result["CPI"], 4 / 3)


def test_risk_monte_carlo_is_reproducible_and_respects_certain_events():
    risks = pd.DataFrame([
        {"risk_id": "R1", "risk_description": "Certain", "probability": 1,
         "cost_impact": 100, "schedule_impact_days": 4},
        {"risk_id": "R2", "risk_description": "Impossible", "probability": 0,
         "cost_impact": 500, "schedule_impact_days": 10},
    ])
    ranked, stats, samples = risk_analysis(risks, iterations=1000, seed=7)
    assert stats["expected_cost_exposure"] == 100
    assert stats["expected_schedule_exposure_days"] == 4
    assert (samples["cost"] == 100).all()
    assert (samples["delay_days"] == 4).all()
    assert ranked.iloc[0]["risk_id"] == "R1"


def test_xer_cpm_respects_relationship_type_and_lag():
    from core import calculate_xer_cpm

    tables = {
        "TASK": pd.DataFrame([
            {"task_id": "T1", "task_code": "A", "task_name": "A", "target_drtn_hr_cnt": 16},
            {"task_id": "T2", "task_code": "B", "task_name": "B", "target_drtn_hr_cnt": 8},
            {"task_id": "T3", "task_code": "C", "task_name": "C", "target_drtn_hr_cnt": 8},
        ]),
        "TASKPRED": pd.DataFrame([
            {"task_id": "T2", "pred_task_id": "T1", "pred_type": "PR_FS", "lag_hr_cnt": 8},
            {"task_id": "T3", "pred_task_id": "T2", "pred_type": "PR_SS", "lag_hr_cnt": 0},
        ]),
    }
    result, stats = calculate_xer_cpm(tables, hours_per_day=8)
    rows = result.set_index("task_id")
    assert rows.loc["T1", "early_start_day"] == 0
    assert rows.loc["T1", "early_finish_day"] == 2
    assert rows.loc["T2", "early_start_day"] == 3
    assert rows.loc["T3", "early_start_day"] == 3
    assert stats["project_duration_days"] == 4


def test_xer_cpm_rejects_missing_relationship_activity():
    from core import calculate_xer_cpm

    tables = {
        "TASK": pd.DataFrame([
            {"task_id": "T1", "task_code": "A", "task_name": "A", "target_drtn_hr_cnt": 8},
        ]),
        "TASKPRED": pd.DataFrame([
            {"task_id": "T1", "pred_task_id": "MISSING", "pred_type": "PR_FS", "lag_hr_cnt": 0},
        ]),
    }
    try:
        calculate_xer_cpm(tables)
    except ValueError as exc:
        assert "unknown activity" in str(exc)
    else:
        raise AssertionError("Missing XER relationship activity must be rejected")


def test_basic_calendar_inclusive_finish_and_holiday():
    from core import add_working_days, calculate_calendar_schedule

    calendars = pd.DataFrame([{
        "calendar_id": "CAL-6", "calendar_name": "Six day", "workdays_per_week": 6,
        "hours_per_day": 8, "holidays": "2026-01-03"
    }])
    assert add_working_days("2026-01-02", 2, "CAL-6", calendars) == "2026-01-05"
    assert add_working_days("2026-01-04", 1, "CAL-6", calendars) == "2026-01-05"
    activities = pd.DataFrame([{
        "activity_id": "A1", "duration_days": 2,
        "planned_start": "2026-01-02", "calendar_id": "CAL-6"
    }])
    result = calculate_calendar_schedule(activities, calendars)
    assert result.iloc[0]["planned_finish_calculated"] == "2026-01-05"
    assert result.iloc[0]["hours_per_day"] == 8


def test_calendar_rejects_unknown_calendar_and_invalid_week():
    from core import add_working_days

    calendars = pd.DataFrame([{
        "calendar_id": "BAD", "calendar_name": "Bad", "workdays_per_week": 4,
        "hours_per_day": 8, "holidays": ""
    }])
    try:
        add_working_days("2026-01-01", 2, "MISSING", calendars)
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Unknown calendar must fail")
    try:
        add_working_days("2026-01-01", 2, "BAD", calendars)
    except ValueError as exc:
        assert "5, 6 or 7" in str(exc)
    else:
        raise AssertionError("Unsupported calendar workweek must fail")


def test_evm_allocates_each_wbs_budget_once_across_activities():
    from core import calculate_evm

    activities = pd.DataFrame([
        {"activity_id":"A1","wbs_id":"1.1","activity_name":"Part 1","duration_days":5,
         "planned_start":"2026-01-01","planned_finish":"2026-01-05","predecessor_ids":"","weight_pct":25},
        {"activity_id":"A2","wbs_id":"1.1","activity_name":"Part 2","duration_days":5,
         "planned_start":"2026-01-01","planned_finish":"2026-01-05","predecessor_ids":"","weight_pct":75},
    ])
    boq = pd.DataFrame([
        {"boq_id":"B1","wbs_id":"1.1","description":"Package","unit":"m3",
         "budget_quantity":100,"unit_rate":10,"budget_amount":1000}
    ])
    progress = pd.DataFrame([
        {"period_end":"2026-01-05","activity_id":"A1","boq_id":"B1","actual_quantity_to_date":100},
        {"period_end":"2026-01-05","activity_id":"A2","boq_id":"B1","actual_quantity_to_date":100},
    ])
    result = calculate_evm(pd.DataFrame(),activities,boq,progress,pd.DataFrame(),"2026-01-05")
    assert result["BAC"] == 1000
    assert result["EV"] == 1000
    assert result["physical_progress_pct"] == 100


def test_evm_rejects_progress_activity_boq_wbs_mismatch():
    from core import calculate_evm

    activities = pd.DataFrame([{
        "activity_id":"A1","wbs_id":"1.1","activity_name":"Work","duration_days":5,
        "planned_start":"2026-01-01","planned_finish":"2026-01-05","predecessor_ids":"","weight_pct":100
    }])
    boq = pd.DataFrame([{
        "boq_id":"B1","wbs_id":"2.1","description":"Other WBS","unit":"m3",
        "budget_quantity":100,"unit_rate":10,"budget_amount":1000
    }])
    progress = pd.DataFrame([{
        "period_end":"2026-01-05","activity_id":"A1","boq_id":"B1","actual_quantity_to_date":50
    }])
    try:
        calculate_evm(pd.DataFrame(),activities,boq,progress,pd.DataFrame(),"2026-01-05")
    except ValueError as exc:
        assert "same WBS" in str(exc)
    else:
        raise AssertionError("Progress across unrelated WBS must be rejected")


def test_evm_rejects_mixed_actual_cost_currencies():
    from core import calculate_evm

    activities = pd.DataFrame([{
        "activity_id":"A1","wbs_id":"1.1","activity_name":"Work","duration_days":5,
        "planned_start":"2026-01-01","planned_finish":"2026-01-05","predecessor_ids":"","weight_pct":100
    }])
    boq = pd.DataFrame([{
        "boq_id":"B1","wbs_id":"1.1","description":"Work","unit":"m3",
        "budget_quantity":100,"unit_rate":10,"budget_amount":1000
    }])
    actual = pd.DataFrame([
        {"transaction_date":"2026-01-02","amount":100,"currency":"IDR"},
        {"transaction_date":"2026-01-03","amount":10,"currency":"USD"},
    ])
    project = pd.DataFrame([{"currency":"IDR"}])
    try:
        calculate_evm(project,activities,boq,pd.DataFrame(),actual,"2026-01-05")
    except ValueError as exc:
        assert "multiple currencies" in str(exc)
    else:
        raise AssertionError("Mixed actual cost currencies must be rejected")


def test_earned_schedule_metrics_produce_time_variance_and_duration_forecast():
    from core import add_earned_schedule_metrics

    project = pd.DataFrame([{
        "planned_start":"2026-01-01", "planned_finish":"2026-01-10", "currency":"IDR"
    }])
    activities = pd.DataFrame([{
        "activity_id":"A1","wbs_id":"1.1","activity_name":"Work","duration_days":10,
        "planned_start":"2026-01-01","planned_finish":"2026-01-10",
        "predecessor_ids":"","weight_pct":100
    }])
    evm = {"BAC":1000.0,"PV":500.0,"EV":400.0,"AC":300.0}
    result = add_earned_schedule_metrics(evm,project,activities,"2026-01-05")
    assert result is evm
    assert result["ES"] == 3.0
    assert result["SV(t)"] == -1.0
    assert result["SPI(t)"] == 0.75
    assert result["IEAC(t)"] == 12.0


def test_commitment_reconciliation_excludes_cancelled_and_prevents_double_counting():
    from core import analyze_commitments

    commitments = pd.DataFrame([
        {"commitment_id":"PO-1","commitment_date":"2026-03-01","committed_amount":1000,
         "paid_amount":250,"currency":"IDR","status":"Active"},
        {"commitment_id":"PO-2","commitment_date":"2026-03-02","committed_amount":500,
         "paid_amount":0,"currency":"IDR","status":"Cancelled"},
        {"commitment_id":"PO-3","commitment_date":"2026-04-01","committed_amount":300,
         "paid_amount":0,"currency":"IDR","status":"Active"},
    ])
    detail, stats = analyze_commitments(commitments, "2026-03-31", "IDR")
    assert list(detail["commitment_id"]) == ["PO-1"]
    assert stats["committed_total"] == 1000
    assert stats["paid_total"] == 250
    assert stats["outstanding_total"] == 750


def test_commitments_reject_overpayment_and_currency_mismatch():
    from core import analyze_commitments

    overpaid = pd.DataFrame([{"commitment_id":"PO-1","committed_amount":100,
        "paid_amount":120,"currency":"IDR","status":"Active"}])
    try:
        analyze_commitments(overpaid, "2026-03-31", "IDR")
    except ValueError as exc:
        assert "cannot exceed" in str(exc)
    else:
        raise AssertionError("Overpaid commitment must be rejected")

    mixed = pd.DataFrame([
        {"commitment_id":"PO-1","committed_amount":100,"paid_amount":0,"currency":"IDR","status":"Active"},
        {"commitment_id":"PO-2","committed_amount":100,"paid_amount":0,"currency":"USD","status":"Active"},
    ])
    try:
        analyze_commitments(mixed, "2026-03-31", "IDR")
    except ValueError as exc:
        assert "multiple currencies" in str(exc)
    else:
        raise AssertionError("Mixed commitment currencies must be rejected")


def test_monthly_cashflow_reconciles_baseline_actual_and_remaining_forecast():
    from core import build_cost_cashflow

    project=pd.DataFrame([{"planned_start":"2026-01-01","planned_finish":"2026-03-31",
        "status_date":"2026-01-31","currency":"IDR"}])
    activities=pd.DataFrame([{"activity_id":"A1","wbs_id":"1.1","activity_name":"Work",
        "duration_days":90,"planned_start":"2026-01-01","planned_finish":"2026-03-31",
        "predecessor_ids":"","weight_pct":100}])
    boq=pd.DataFrame([{"boq_id":"B1","wbs_id":"1.1","description":"Work","unit":"lot",
        "budget_quantity":1,"unit_rate":900,"budget_amount":900}])
    actual=pd.DataFrame([{"transaction_date":"2026-01-15","amount":100,"currency":"IDR"}])
    commitments=pd.DataFrame([{"commitment_id":"PO1","commitment_date":"2026-01-10",
        "committed_amount":300,"paid_amount":100,"currency":"IDR","status":"Active"}])
    progress=pd.DataFrame()
    cashflow,stats,_=build_cost_cashflow(project,activities,boq,actual,commitments,
        "2026-01-31",progress)
    assert round(cashflow["baseline_cost"].sum(),2)==900
    assert stats["actual_to_date"]==100
    assert stats["forecast_at_completion"]==900
    assert stats["remaining_forecast"]==800
    assert stats["commitment_outstanding"]==200
    assert round(cashflow["remaining_forecast"].sum(),2)==800


def test_cashflow_rejects_invalid_activity_dates_and_mixed_actual_currency():
    from core import build_cost_cashflow

    project=pd.DataFrame([{"planned_start":"2026-01-01","planned_finish":"2026-02-28","currency":"IDR"}])
    activities=pd.DataFrame([{"activity_id":"A1","wbs_id":"1.1","activity_name":"Work",
        "duration_days":10,"planned_start":"2026-02-10","planned_finish":"2026-01-10",
        "predecessor_ids":"","weight_pct":100}])
    boq=pd.DataFrame([{"boq_id":"B1","wbs_id":"1.1","description":"Work","unit":"lot",
        "budget_quantity":1,"unit_rate":100,"budget_amount":100}])
    try:
        build_cost_cashflow(project,activities,boq,pd.DataFrame(),pd.DataFrame(),"2026-01-31")
    except ValueError as exc:
        assert "Activity dates" in str(exc)
    else:
        raise AssertionError("Invalid activity date range must fail")

    activities.loc[0,"planned_start"]="2026-01-01"
    activities.loc[0,"planned_finish"]="2026-01-10"
    actual=pd.DataFrame([
        {"transaction_date":"2026-01-02","amount":10,"currency":"IDR"},
        {"transaction_date":"2026-01-03","amount":10,"currency":"USD"},
    ])
    try:
        build_cost_cashflow(project,activities,boq,actual,pd.DataFrame(),"2026-01-31")
    except ValueError as exc:
        assert "currency" in str(exc).lower()
    else:
        raise AssertionError("Mixed actual cost currencies must fail")


def test_resource_load_capacity_utilization_and_validation():
    from core import calculate_resource_load

    resources = pd.DataFrame([
        {"rsrc_id":"CR-01","rsrc_name":"Mobile Crane","rsrc_type":"Equipment",
         "unit_of_measure":"hour","capacity_per_day":8}
    ])
    assignments = pd.DataFrame([
        {"task_id":"A1","rsrc_id":"CR-01","target_qty":24,"actual_qty":12,
         "target_cost":300,"actual_cost":120,
         "target_start_date":"2026-01-01","target_end_date":"2026-01-03"},
        {"task_id":"A2","rsrc_id":"CR-01","target_qty":12,"actual_qty":0,
         "target_cost":100,"actual_cost":0,
         "target_start_date":"2026-01-02","target_end_date":"2026-01-03"},
    ])
    summary, daily = calculate_resource_load(resources, assignments)
    assert len(daily) == 3
    jan2 = daily.loc[daily["date"] == pd.Timestamp("2026-01-02")].iloc[0]
    assert jan2["planned_load_per_day"] == 12
    assert jan2["capacity_utilization_pct"] == 150
    assert bool(jan2["over_capacity"])
    assert summary.iloc[0]["overloaded_days"] == 2
    assert summary.iloc[0]["peak_capacity_utilization_pct"] == 150

    invalid = assignments.copy()
    invalid.loc[0, "target_qty"] = -1
    try:
        calculate_resource_load(resources, invalid)
    except ValueError as exc:
        assert "target_qty" in str(exc)
    else:
        raise AssertionError("Negative resource quantity must be rejected")


def test_resource_load_rejects_unknown_resource_and_invalid_dates():
    from core import calculate_resource_load

    resources = pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":8}])
    assignments = pd.DataFrame([{"rsrc_id":"MISSING","target_qty":1,
        "target_start_date":"2026-01-01","target_end_date":"2026-01-02"}])
    try:
        calculate_resource_load(resources, assignments)
    except ValueError as exc:
        assert "unknown resources" in str(exc)
    else:
        raise AssertionError("Unknown resource must be rejected")

    assignments.loc[0,"rsrc_id"]="R1"
    assignments.loc[0,"target_end_date"]="2025-12-31"
    try:
        calculate_resource_load(resources, assignments)
    except ValueError as exc:
        assert "date range" in str(exc)
    else:
        raise AssertionError("Invalid date range must be rejected")
