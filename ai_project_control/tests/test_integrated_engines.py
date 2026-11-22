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
