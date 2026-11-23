from ai_project_control.project_director_review import build_project_director_review


def test_review_keeps_resource_and_risk_evidence_separate_from_matrix_inputs():
    result = build_project_director_review(
        {"project_id": "P1", "project_name": "Mine Development"},
        {"project_id": "P1", "SPI": 0.9, "CPI": 0.92},
        risk_simulation={"status": "ASSESSED", "probability_over_base": 35.0,
                         "p80_contingency": 120, "currency": "IDR"},
        resource_summary={"overloaded_count": 3, "unassessed_count": 1},
        schedule_forecast={"delayed_activity_ids": ["A1"], "unassessed_activity_ids": []},
    )
    assert result["decision"]["priority"] == "DATA_REVIEW"
    assert result["decision"]["risk_score"] is None
    assert result["decision"]["overloaded_resource_days"] is None
    assert result["summary"]["attention_count"] == 4


def test_review_does_not_call_missing_inputs_stable():
    result = build_project_director_review(
        {"project_id": "P2"}, {"SPI": None, "CPI": None}
    )
    assert result["status"] == "UNASSESSED"
    assert result["summary"]["unassessed_count"] == 2
