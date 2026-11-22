import pandas as pd

from core import calculate_dcma14, calculate_xer_cpm


def test_dcma14_does_not_flag_single_activity_as_missing_logic():
    tables = {
        "TASK": pd.DataFrame([{
            "task_id": "T1",
            "task_code": "A1",
            "status_code": "TK_NotStart",
            "early_start_date": "2026-01-01",
            "early_end_date": "2026-01-01",
            "target_end_date": "2026-01-01",
            "target_drtn_hr_cnt": 8,
            "remain_drtn_hr_cnt": 8,
            "total_float_hr_cnt": 0,
        }]),
        "TASKPRED": pd.DataFrame(columns=["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"]),
    }

    result = calculate_dcma14(tables)
    logic = result.loc[result["DCMA Point"] == 1].iloc[0]
    assert logic["Flagged"] == 0
    assert logic["RAG"] == "Green"


def test_xer_cpm_supports_all_four_p6_relationship_types_and_lag():
    task = pd.DataFrame([
        {"task_id": "A", "task_code": "A", "task_name": "Start", "target_drtn_hr_cnt": 16},
        {"task_id": "B", "task_code": "B", "task_name": "SS successor", "target_drtn_hr_cnt": 8},
        {"task_id": "C", "task_code": "C", "task_name": "FF successor", "target_drtn_hr_cnt": 8},
        {"task_id": "D", "task_code": "D", "task_name": "SF successor", "target_drtn_hr_cnt": 8},
    ])
    relationships = pd.DataFrame([
        {"task_id": "B", "pred_task_id": "A", "pred_type": "PR_SS", "lag_hr_cnt": 8},
        {"task_id": "C", "pred_task_id": "A", "pred_type": "PR_FF", "lag_hr_cnt": 0},
        {"task_id": "D", "pred_task_id": "A", "pred_type": "PR_SF", "lag_hr_cnt": 0},
    ])

    result, stats = calculate_xer_cpm({"TASK": task, "TASKPRED": relationships})
    by_id = result.set_index("task_id")
    assert by_id.loc["A", "early_start_day"] == 0
    assert by_id.loc["B", "early_start_day"] == 1
    assert by_id.loc["C", "early_start_day"] == 1
    assert by_id.loc["D", "early_start_day"] == 0
    assert stats["relationship_count"] == 3
