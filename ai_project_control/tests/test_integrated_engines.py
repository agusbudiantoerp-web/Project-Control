import pandas as pd
import pytest
from core import calculate_cpm, parse_xer, calculate_xer_cpm, risk_analysis, calculate_schedule_pert

def test_cpm_forward_backward_and_critical_path():
    frame=pd.DataFrame([
      {'activity_id':'A','activity_name':'A','wbs_id':'1','duration_days':3,'predecessor_ids':'','weight_pct':40},
      {'activity_id':'B','activity_name':'B','wbs_id':'1','duration_days':4,'predecessor_ids':'A','weight_pct':40},
      {'activity_id':'C','activity_name':'C','wbs_id':'1','duration_days':2,'predecessor_ids':'A','weight_pct':20},
    ])
    result,stats=calculate_cpm(frame)
    assert stats['project_duration']==7
    assert set(result.loc[result['is_critical'],'activity_id'])=={'A','B'}

def test_cpm_rejects_cycles():
    frame=pd.DataFrame([
      {'activity_id':'A','activity_name':'A','wbs_id':'1','duration_days':3,'predecessor_ids':'B'},
      {'activity_id':'B','activity_name':'B','wbs_id':'1','duration_days':4,'predecessor_ids':'A'},
    ])
    with pytest.raises(ValueError): calculate_cpm(frame)

def test_xer_parser_and_cpm():
    raw=b'%T\tTASK\n%F\ttask_id\ttask_code\ttask_name\ttarget_drtn_hr_cnt\n%R\t1\tA\tAlpha\t16\n%R\t2\tB\tBeta\t8\n%T\tTASKPRED\n%F\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n%R\t2\t1\tPR_FS\t0\n%E\n'
    tables=parse_xer(raw)
    result,stats=calculate_xer_cpm(tables)
    assert stats['project_duration_days']==3
    assert result['critical'].all()

def test_risk_exposure_and_reproducibility():
    frame=pd.DataFrame([{'risk_id':'R1','risk_description':'rain','probability':0.5,'cost_impact':100,'schedule_impact_days':2}])
    _,stats,samples=risk_analysis(frame,1000,seed=7)
    assert stats['expected_cost_exposure']==50
    assert len(samples)==1000

def test_pert_handles_zero_duration_milestones():
    frame=pd.DataFrame([{'activity_id':'M','activity_name':'Milestone','wbs_id':'1','duration_days':0,'predecessor_ids':'','weight_pct':100}])
    _,stats,_=calculate_schedule_pert(frame,1000)
    assert stats['mc_p50']==0

def test_wbs_weighted_evm_allocation():
    from core import calculate_evm
    project=pd.DataFrame([{"planned_start":"2026-01-01","planned_finish":"2026-01-10"}])
    activities=pd.DataFrame([
      {"activity_id":"A","wbs_id":"1","duration_days":5,"planned_start":"2026-01-01","planned_finish":"2026-01-10","weight_pct":50},
      {"activity_id":"B","wbs_id":"1","duration_days":5,"planned_start":"2026-01-01","planned_finish":"2026-01-10","weight_pct":50},
    ])
    boq=pd.DataFrame([{"boq_id":"Q1","wbs_id":"1","budget_quantity":100,"unit_rate":10,"budget_amount":1000}])
    progress=pd.DataFrame([
      {"period_end":"2026-01-20","activity_id":"A","boq_id":"Q1","actual_quantity_to_date":50},
      {"period_end":"2026-01-20","activity_id":"B","boq_id":"Q1","actual_quantity_to_date":50},
    ])
    actual=pd.DataFrame([{"transaction_date":"2026-01-20","amount":400}])
    result=calculate_evm(project,activities,boq,progress,actual,"2026-01-20")
    assert result["BAC"]==1000
    assert result["EV"]==500
    assert result["AC"]==400

def test_milestone_and_change_register_metrics():
    from core import calculate_milestones, calculate_change_impact
    milestones=pd.DataFrame([{"milestone_id":"M1","milestone_name":"Gate","planned_date":"2026-01-10","forecast_date":"2026-01-12","actual_date":"","status":"At Risk","owner":"PM"}])
    result,stats=calculate_milestones(milestones,"2026-01-11")
    assert stats["total"]==1
    assert stats["delayed"]==1
    changes=pd.DataFrame([{"change_id":"C1","date_raised":"2026-01-01","description":"Scope","cost_impact":100,"schedule_impact_days":2,"status":"Approved"}])
    _,impact=calculate_change_impact(changes,1000)
    assert impact["revised_budget"]==1100

def test_resource_load_rollup():
    from core import calculate_resource_load
    resources=pd.DataFrame([{"rsrc_id":"R1","rsrc_name":"Crane","rsrc_type":"Equipment","capacity_per_day":8}])
    assignments=pd.DataFrame([{"task_id":"A1","rsrc_id":"R1","target_qty":40,"actual_qty":30,
      "target_cost":100,"actual_cost":80,"target_start_date":"2026-01-01","target_end_date":"2026-01-05"}])
    summary,daily=calculate_resource_load(resources,assignments)
    assert summary.iloc[0]["target_qty"]==40
    assert len(daily)==5
    assert not daily["over_capacity"].any()


def test_schedule_only_xer_activity_weights_can_be_zero():
    from core import validate_dataset
    frame=pd.DataFrame([{"activity_id":"A","wbs_id":"1","activity_name":"A","duration_days":1,
      "planned_start":"2026-01-01","planned_finish":"2026-01-01","predecessor_ids":"","weight_pct":0}])
    assert validate_dataset("activities.csv",frame,{})==[]

def test_milestone_forecast_slippage_is_counted_before_due_date():
    from core import calculate_milestones
    milestones=pd.DataFrame([{"milestone_id":"M1","milestone_name":"Gate","planned_date":"2026-01-10",
      "forecast_date":"2026-01-12","actual_date":"","status":"At Risk","owner":"PM"}])
    _,stats=calculate_milestones(milestones,"2026-01-11")
    assert stats["delayed"]==1
    assert stats["at_risk"]==1

def test_backup_roundtrip_restores_project_datasets(tmp_path,monkeypatch):
    import core
    monkeypatch.setattr(core,"DATA_DIR",tmp_path)
    monkeypatch.setattr(core,"DB_PATH",tmp_path/"test.db")
    core.init_db()
    frame=pd.DataFrame([{"project_id":"P1","project_name":"Test","planned_start":"2026-01-01",
      "planned_finish":"2026-12-31","status_date":"2026-01-31","currency":"IDR"}])
    core.save_dataset("P1","project_master.csv",frame)
    raw=core.export_project_backup("P1")
    core.import_project_backup("P2",raw)
    restored=core.load_dataset("P2","project_master.csv")
    assert restored.iloc[0]["project_name"]=="Test"


def test_progress_engine_returns_weighted_physical_progress():
    from core import calculate_progress
    activities=pd.DataFrame([
      {"activity_id":"A","wbs_id":"1","activity_name":"A","duration_days":5,"planned_start":"2026-01-01","planned_finish":"2026-01-05","weight_pct":100}
    ])
    boq=pd.DataFrame([{"boq_id":"Q1","wbs_id":"1","budget_quantity":100,"unit_rate":10,"budget_amount":1000}])
    progress=pd.DataFrame([{"period_end":"2026-01-05","activity_id":"A","boq_id":"Q1","actual_quantity_to_date":40}])
    result,stats=calculate_progress(activities,progress,boq)
    assert stats["weighted_progress_pct"]==40
    assert stats["reported_activities"]==1
    assert len(result)==1


def test_risk_analysis_is_seed_reproducible_and_chunked():
    risks = pd.DataFrame([
        {"risk_id": f"R{i}", "probability": 0.35, "cost_impact": i * 100,
         "schedule_impact_days": i % 7}
        for i in range(1, 151)
    ])
    _, stats_a, samples_a = risk_analysis(risks, 25000, seed=123)
    _, stats_b, samples_b = risk_analysis(risks, 25000, seed=123)

    assert stats_a == stats_b
    pd.testing.assert_frame_equal(samples_a, samples_b)
    assert len(samples_a) == 25000
    assert samples_a["cost"].ge(0).all()
    assert samples_a["delay_days"].ge(0).all()


def test_risk_analysis_rejects_invalid_seed_and_iteration_count():
    risks = pd.DataFrame([{"risk_id": "R1", "probability": 0.5,
                           "cost_impact": 100, "schedule_impact_days": 2}])
    with pytest.raises(ValueError):
        risk_analysis(risks, 99)


def test_schedule_pert_rejects_invalid_duration_and_duplicate_activity_ids():
    invalid = pd.DataFrame([
        {"activity_id": "A", "duration_days": -2, "predecessor_ids": ""}
    ])
    with pytest.raises(ValueError, match="finite dan tidak negatif"):
        calculate_schedule_pert(invalid, 1000)

    duplicate = pd.DataFrame([
        {"activity_id": "A", "duration_days": 2, "predecessor_ids": ""},
        {"activity_id": "A", "duration_days": 3, "predecessor_ids": ""},
    ])
    with pytest.raises(ValueError, match="terisi dan unik"):
        calculate_schedule_pert(duplicate, 1000)


def test_schedule_pert_rejects_non_numeric_and_non_finite_duration():
    for value in ["unknown", float("inf"), float("nan")]:
        frame = pd.DataFrame([
            {"activity_id": "A", "duration_days": value, "predecessor_ids": ""}
        ])
        with pytest.raises(ValueError, match="finite dan tidak negatif"):
            calculate_schedule_pert(frame, 1000)


def test_schedule_pert_rejects_invalid_iteration_count():
    frame = pd.DataFrame([
        {"activity_id": "A", "duration_days": 5, "predecessor_ids": ""}
    ])
    with pytest.raises(ValueError, match="minimal 100"):
        calculate_schedule_pert(frame, 99)


def test_evm_rejects_duplicate_progress_rows_in_same_reporting_period():
    from core import calculate_evm

    project = pd.DataFrame([{"currency": "IDR"}])
    activities = pd.DataFrame([{"activity_id": "A1", "wbs_id": "1",
        "planned_start": "2026-01-01", "planned_finish": "2026-01-10", "weight_pct": 100}])
    boq = pd.DataFrame([{"boq_id": "Q1", "wbs_id": "1", "budget_quantity": 100,
        "unit_rate": 10, "budget_amount": 1000}])
    progress = pd.DataFrame([
        {"period_end": "2026-01-05", "activity_id": "A1", "boq_id": "Q1", "actual_quantity_to_date": 20},
        {"period_end": "2026-01-05", "activity_id": "A1", "boq_id": "Q1", "actual_quantity_to_date": 25},
    ])

    with pytest.raises(ValueError, match="duplicate rows"):
        calculate_evm(project, activities, boq, progress, pd.DataFrame(), "2026-01-05")

def test_evm_rejects_cumulative_progress_above_boq_quantity():
    from core import calculate_evm

    project = pd.DataFrame([{"currency": "IDR"}])
    activities = pd.DataFrame([{"activity_id": "A1", "wbs_id": "1",
        "planned_start": "2026-01-01", "planned_finish": "2026-01-10", "weight_pct": 100}])
    boq = pd.DataFrame([{"boq_id": "Q1", "wbs_id": "1", "budget_quantity": 100,
        "unit_rate": 10, "budget_amount": 1000}])
    progress = pd.DataFrame([{"period_end": "2026-01-05", "activity_id": "A1",
        "boq_id": "Q1", "actual_quantity_to_date": 125}])

    with pytest.raises(ValueError, match="exceeds BOQ budget quantity"):
        calculate_evm(project, activities, boq, progress, pd.DataFrame(), "2026-01-05")
def test_progress_engine_rejects_duplicate_same_period_activity_boq_rows():
    from core import calculate_progress

    activities = pd.DataFrame([{"activity_id": "A1", "wbs_id": "1", "weight_pct": 100}])
    progress = pd.DataFrame([
        {"period_end": "2026-01-05", "activity_id": "A1", "boq_id": "Q1", "actual_quantity_to_date": 20},
        {"period_end": "2026-01-05", "activity_id": "A1", "boq_id": "Q1", "actual_quantity_to_date": 25},
    ])
    with pytest.raises(ValueError, match="duplicate rows"):
        calculate_progress(activities, progress)

def test_progress_engine_rejects_unknown_activity_reference():
    from core import calculate_progress

    activities = pd.DataFrame([{"activity_id": "A1", "wbs_id": "1", "weight_pct": 100}])
    progress = pd.DataFrame([{
        "period_end": "2026-01-05", "activity_id": "A-UNKNOWN",
        "actual_quantity_to_date": 10,
    }])
    with pytest.raises(ValueError, match="unknown activities"):
        calculate_progress(activities, progress)

def test_evm_rejects_blank_boq_identifiers():
    from core import calculate_evm

    project = pd.DataFrame([{"currency": "IDR"}])
    activities = pd.DataFrame([{"activity_id": "A1", "wbs_id": "1",
        "planned_start": "2026-01-01", "planned_finish": "2026-01-10", "weight_pct": 100}])
    boq = pd.DataFrame([{"boq_id": "", "wbs_id": "1", "budget_quantity": 100,
        "unit_rate": 10, "budget_amount": 1000}])
    with pytest.raises(ValueError, match="blank boq_id"):
        calculate_evm(project, activities, boq, pd.DataFrame(), pd.DataFrame(), "2026-01-05")

def test_evm_rejects_blank_activity_and_wbs_identifiers():
    from core import calculate_evm

    project = pd.DataFrame([{"currency": "IDR"}])
    activities = pd.DataFrame([{"activity_id": "", "wbs_id": "1",
        "planned_start": "2026-01-01", "planned_finish": "2026-01-10", "weight_pct": 100}])
    boq = pd.DataFrame([{"boq_id": "Q1", "wbs_id": "1", "budget_quantity": 100,
        "unit_rate": 10, "budget_amount": 1000}])
    with pytest.raises(ValueError, match="blank activity_id"):
        calculate_evm(project, activities, boq, pd.DataFrame(), pd.DataFrame(), "2026-01-05")

def test_evm_rejects_activity_finish_before_start():
    from core import calculate_evm

    project = pd.DataFrame([{"currency": "IDR"}])
    activities = pd.DataFrame([{"activity_id": "A1", "wbs_id": "1",
        "planned_start": "2026-01-10", "planned_finish": "2026-01-01", "weight_pct": 100}])
    boq = pd.DataFrame([{"boq_id": "Q1", "wbs_id": "1", "budget_quantity": 100,
        "unit_rate": 10, "budget_amount": 1000}])
    with pytest.raises(ValueError, match="planned_finish cannot be earlier"):
        calculate_evm(project, activities, boq, pd.DataFrame(), pd.DataFrame(), "2026-01-05")

def test_cpm_rejects_blank_duplicate_and_invalid_activity_ids():
    base={"activity_name":"Task","wbs_id":"1","duration_days":2,"predecessor_ids":""}
    for rows in [
        [{**base,"activity_id":""}],
        [{**base,"activity_id":"A"},{**base,"activity_id":"A"}],
    ]:
        with pytest.raises(ValueError, match="activity_id harus terisi dan unik"):
            calculate_cpm(pd.DataFrame(rows))


def test_cpm_rejects_non_finite_or_negative_durations():
    for value in [-1, "unknown", float("inf"), float("nan")]:
        frame=pd.DataFrame([{"activity_id":"A","duration_days":value,"predecessor_ids":""}])
        with pytest.raises(ValueError, match="duration_days harus berupa angka finite"):
            calculate_cpm(frame)


def test_cpm_rejects_unknown_and_self_predecessors():
    unknown=pd.DataFrame([{"activity_id":"A","duration_days":2,"predecessor_ids":"MISSING"}])
    with pytest.raises(ValueError, match="predecessor tidak ditemukan"):
        calculate_cpm(unknown)
    self_link=pd.DataFrame([{"activity_id":"A","duration_days":2,"predecessor_ids":"A"}])
    with pytest.raises(ValueError, match="tidak boleh menjadi predecessor dirinya sendiri"):
        calculate_cpm(self_link)
