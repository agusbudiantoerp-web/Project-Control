import pytest

from ai_project_control.data_quality_validation import validate_project_control_data


def test_valid_linked_project_records():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "boq": [{"project_id": "P1", "boq_id": "B1", "quantity": 2, "unit_rate": 10, "amount": 20}],
        "activities": [{"project_id": "P1", "activity_id": "A1", "duration_days": 5}],
        "progress": [{"project_id": "P1", "activity_id": "A1", "period": "2026-01", "physical_progress_pct": 25}],
    })
    assert result["status"] == "VALID"
    assert result["error_count"] == 0


def test_unknown_project_reference_is_error():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "risk": [{"project_id": "P2", "risk_id": "R1"}],
    })
    assert result["status"] == "INVALID"
    assert any(issue["code"] == "UNKNOWN_PROJECT" for issue in result["issues"])


def test_duplicate_business_key_is_error():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}, {"project_id": "P1"}],
    })
    assert any(issue["code"] == "DUPLICATE_KEY" for issue in result["issues"])


def test_invalid_numeric_and_progress_range_are_errors():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "progress": [
            {"project_id": "P1", "activity_id": "A1", "period": "2026-01",
             "physical_progress_pct": 140},
            {"project_id": "P1", "activity_id": "A2", "period": "2026-01",
             "physical_progress_pct": "not-a-number"},
        ],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "PERCENT_OUT_OF_RANGE" in codes
    assert "INVALID_NUMBER" in codes


def test_missing_project_key_and_negative_quantity_are_errors():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "boq": [{"project_id": "P1", "boq_id": "", "quantity": -2}],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "MISSING_KEY" in codes
    assert "NEGATIVE_VALUE" in codes


def test_input_is_not_mutated_and_empty_optional_tables_are_not_claimed_clean():
    source = {"project_master": [{"project_id": "P1"}]}
    before = {"project_master": [{"project_id": "P1"}]}
    result = validate_project_control_data(source)
    assert source == before
    assert result["validated_tables"]["actual_cost"] == 0
    assert any("not evidence" in item for item in result["limitations"])


def test_wrong_table_shape_is_reported():
    result = validate_project_control_data({"project_master": "not-a-list"})
    assert result["status"] == "INVALID"
    assert result["issues"][0]["code"] == "TABLE_NOT_A_LIST"


def test_non_dictionary_input_rejected():
    with pytest.raises(TypeError):
        validate_project_control_data([])


def test_risk_probability_must_be_fraction_between_zero_and_one():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "risk": [{"project_id": "P1", "risk_id": "R1", "probability": 75,
                 "cost_impact_min": 100, "cost_impact_most_likely": 200,
                 "cost_impact_max": 300}],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "PROBABILITY_OUT_OF_RANGE" in codes


def test_boolean_numeric_fields_are_rejected():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1", "BAC": True}],
        "progress": [{
            "project_id": "P1", "activity_id": "A1", "period": "2026-11",
            "planned_value": 100, "earned_value": 80,
        }],
        "actual_cost": [{
            "project_id": "P1", "period": "2026-11", "cost_code": "C1",
            "actual_cost": False,
        }],
    })
    assert result["status"] == "INVALID"
    assert sum(issue["code"] == "INVALID_NUMBER" for issue in result["issues"]) == 2


def test_negative_evm_financial_amounts_are_rejected():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1", "BAC": -100}],
        "progress": [{
            "project_id": "P1", "activity_id": "A1", "period": "2026-11",
            "planned_value": 100, "earned_value": -10,
        }],
        "actual_cost": [{
            "project_id": "P1", "period": "2026-11", "cost_code": "C1",
            "actual_cost": -5,
        }],
    })
    assert result["status"] == "INVALID"
    assert sum(issue["code"] == "NEGATIVE_VALUE" for issue in result["issues"]) == 3


def test_risk_score_is_validated_when_supplied():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "risk": [{
            "project_id": "P1", "risk_id": "R1",
            "probability": 0.5, "impact": 10, "risk_score": 101,
        }],
    })
    assert result["status"] == "INVALID"
    assert any(issue["code"] == "RISK_SCORE_OUT_OF_RANGE" for issue in result["issues"])


def test_boq_amount_must_match_quantity_times_unit_rate():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "boq": [{
            "project_id": "P1", "boq_id": "B1",
            "quantity": 12.5, "unit_rate": 250000, "amount": 3125000,
        }],
    })
    assert result["status"] == "VALID"
    assert not any(issue["code"] == "BOQ_AMOUNT_MISMATCH" for issue in result["issues"])


def test_boq_amount_mismatch_is_rejected():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "boq": [{
            "project_id": "P1", "boq_id": "B1",
            "quantity": 12.5, "unit_rate": 250000, "amount": 2500000,
        }],
    })
    assert result["status"] == "INVALID"
    issue = next(issue for issue in result["issues"] if issue["code"] == "BOQ_AMOUNT_MISMATCH")
    assert issue["field"] == "amount"


def test_boq_amount_check_allows_rounding_tolerance():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "boq": [{
            "project_id": "P1", "boq_id": "B1",
            "quantity": 3, "unit_rate": 100.3333, "amount": 301,
        }],
    })
    assert result["status"] == "VALID"


def test_unknown_wbs_parent_and_hierarchy_cycle_are_rejected():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "wbs": [
            {"project_id": "P1", "wbs_id": "W1", "parent_wbs_id": "W2"},
            {"project_id": "P1", "wbs_id": "W2", "parent_wbs_id": "W1"},
        ],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "WBS_HIERARCHY_CYCLE" in codes


def test_activity_wbs_and_predecessor_links_must_exist():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "wbs": [{"project_id": "P1", "wbs_id": "W1"}],
        "activities": [
            {"project_id": "P1", "activity_id": "A1", "wbs_id": "MISSING",
             "predecessor_ids": "A2"},
            {"project_id": "P1", "activity_id": "A2", "wbs_id": "W1",
             "predecessor_ids": "UNKNOWN"},
        ],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "UNKNOWN_ACTIVITY_WBS" in codes
    assert "UNKNOWN_ACTIVITY_PREDECESSOR" in codes


def test_boq_progress_and_actual_cost_links_are_checked():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "wbs": [{"project_id": "P1", "wbs_id": "W1"}],
        "activities": [{"project_id": "P1", "activity_id": "A1", "wbs_id": "W1"}],
        "boq": [{"project_id": "P1", "boq_id": "B1", "wbs_id": "W1",
                 "quantity": 1, "unit_rate": 10, "amount": 10}],
        "progress": [{"project_id": "P1", "activity_id": "MISSING", "boq_id": "B2",
                      "period": "2026-11"}],
        "actual_cost": [{"project_id": "P1", "period": "2026-11", "cost_code": "C1",
                         "boq_id": "B3", "wbs_id": "W2", "actual_cost": 5}],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "UNKNOWN_PROGRESS_ACTIVITY" in codes
    assert "UNKNOWN_PROGRESS_BOQ" in codes
    assert "UNKNOWN_COST_BOQ" in codes
    assert "UNKNOWN_COST_WBS" in codes


def test_boq_and_progress_wbs_consistency_is_enforced():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "wbs": [
            {"project_id": "P1", "wbs_id": "W1"},
            {"project_id": "P1", "wbs_id": "W2"},
        ],
        "activities": [{"project_id": "P1", "activity_id": "A1", "wbs_id": "W1"}],
        "boq": [{"project_id": "P1", "boq_id": "B1", "wbs_id": "W2",
                 "activity_id": "A1", "quantity": 1, "unit_rate": 10, "amount": 10}],
        "progress": [{"project_id": "P1", "activity_id": "A1", "boq_id": "B1",
                      "period": "2026-11"}],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "BOQ_ACTIVITY_WBS_MISMATCH" in codes
    assert "PROGRESS_ACTIVITY_BOQ_WBS_MISMATCH" in codes
