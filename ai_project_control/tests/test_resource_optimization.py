import pandas as pd
from resource_optimization import simulate_resource_smoothing


def test_resource_smoothing_shifts_noncritical_work_within_float():
    activities=pd.DataFrame([
        {"activity_id":"A","activity_name":"Critical","wbs_id":"1","duration_days":2,"predecessor_ids":""},
        {"activity_id":"B","activity_name":"Noncritical","wbs_id":"1","duration_days":2,"predecessor_ids":""},
    ])
    resources=pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":5}])
    assignments=pd.DataFrame([
        {"task_id":"A","rsrc_id":"R1","target_qty":10,"target_start_date":"2026-01-01","target_end_date":"2026-01-02"},
        {"task_id":"B","rsrc_id":"R1","target_qty":10,"target_start_date":"2026-01-01","target_end_date":"2026-01-02"},
    ])
    result=simulate_resource_smoothing(activities,resources,assignments,max_shift_days=30)
    assert result["available"]
    assert result["baseline_overloaded_days"]==2
    shifted=result["scenario"].set_index("task_id").loc["B"]
    assert shifted["shift_days"]>0
    assert shifted["remaining_float_days"]>=0
    assert result["scenario_overloaded_days"]<result["baseline_overloaded_days"]


def test_resource_smoothing_requires_valid_capacity():
    activities=pd.DataFrame([{"activity_id":"A","duration_days":2,"predecessor_ids":""}])
    resources=pd.DataFrame([{"rsrc_id":"R1","capacity_per_day":0}])
    assignments=pd.DataFrame([{"task_id":"A","rsrc_id":"R1","target_qty":2,
        "target_start_date":"2026-01-01","target_end_date":"2026-01-02"}])
    try:
        simulate_resource_smoothing(activities,resources,assignments)
    except ValueError as exc:
        assert "capacity" in str(exc)
    else:
        raise AssertionError("Invalid capacity should be rejected")
