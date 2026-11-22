import pandas as pd
import pytest
from core import calculate_cpm, parse_xer, calculate_xer_cpm, risk_analysis

def test_cpm_forward_backward_and_critical_path():
    frame=pd.DataFrame([
      {'activity_id':'A','activity_name':'A','wbs_id':'1','duration_days':3,'predecessor_ids':''},
      {'activity_id':'B','activity_name':'B','wbs_id':'1','duration_days':4,'predecessor_ids':'A'},
      {'activity_id':'C','activity_name':'C','wbs_id':'1','duration_days':2,'predecessor_ids':'A'},
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

def test_risk_exposure_reproducibility():
    frame=pd.DataFrame([{'risk_id':'R1','risk_description':'rain','probability':0.5,'cost_impact':100,'schedule_impact_days':2}])
    _,stats,samples=risk_analysis(frame,1000,seed=7)
    assert stats['expected_cost_exposure']==50
    assert len(samples)==1000