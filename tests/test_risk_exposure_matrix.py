import pytest

from ai_project_control.risk_exposure_matrix import build_risk_exposure_matrix


def activities():
    return [
        {"activity_id": "A1", "duration_days": 5, "predecessors": []},
        {"activity_id": "A2", "duration_days": 3, "predecessors": ["A1"]},
        {"activity_id": "B1", "duration_days": 2, "predecessors": []},
    ]


def test_ranks_risks_and_identifies_critical_activity_and_wbs_links():
    risks = [
        {"risk_id": "R1", "probability": .8, "impact": 10, "activity_id": "A2",
         "wbs_id": "W2", "category": "SCHEDULE"},
        {"risk_id": "R2", "probability": .2, "impact": 2, "activity_id": "B1",
         "wbs_id": "W1", "mitigation": "Vendor expediting plan"},
    ]
    result = build_risk_exposure_matrix(
        risks, activities=activities(),
        wbs=[{"wbs_id": "W1"}, {"wbs_id": "W2"}],
    )
    assert result["status"] == "ASSESSED"
    assert result["risks"][0]["risk_id"] == "R1"
    assert result["risks"][0]["priority"] == "CRITICAL"
    assert result["risks"][0]["is_critical_activity"] is True
    assert result["risks"][0]["activity_link_status"] == "MATCHED"
    assert result["risks"][0]["wbs_link_status"] == "MATCHED"
    assert result["risks"][0]["mitigation_recommendation"]


def test_unknown_references_are_flagged_not_inferred():
    result = build_risk_exposure_matrix(
        [{"risk_id": "R1", "probability": .5, "impact": 3,
          "activity_id": "MISSING", "wbs_id": "WBS-X"}],
        activities=activities(), wbs=[{"wbs_id": "W1"}],
    )
    risk = result["risks"][0]
    assert risk["activity_link_status"] == "UNKNOWN_ACTIVITY"
    assert risk["wbs_link_status"] == "UNKNOWN_WBS"
    assert risk["is_critical_activity"] is None


def test_empty_register_is_not_zero_risk():
    result = build_risk_exposure_matrix([])
    assert result["status"] == "NO_RISKS"
    assert result["risk_count"] == 0


def test_invalid_probability_and_missing_impact_rejected():
    with pytest.raises(ValueError, match="probability"):
        build_risk_exposure_matrix([{"risk_id": "R1", "probability": 2, "impact": 1}])
    with pytest.raises(ValueError, match="impact"):
        build_risk_exposure_matrix([{"risk_id": "R1", "probability": .5}])


def test_mixed_thresholds_and_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="thresholds"):
        build_risk_exposure_matrix([], impact_medium_threshold=5, impact_high_threshold=2)
    with pytest.raises(ValueError, match="duplicate"):
        build_risk_exposure_matrix([
            {"risk_id": "R1", "probability": .5, "impact": 2},
            {"risk_id": "R1", "probability": .5, "impact": 2},
        ])


def test_no_activity_network_does_not_claim_critical_mapping():
    result = build_risk_exposure_matrix([
        {"risk_id": "R1", "probability": .9, "impact": 9, "activity_id": "A1"}
    ])
    assert result["risks"][0]["is_critical_activity"] is False
    assert result["risks"][0]["activity_link_status"] == "UNKNOWN_ACTIVITY"


def test_rejects_boolean_risk_inputs_and_overflowing_exposure():
    with pytest.raises(ValueError, match="not boolean"):
        build_risk_exposure_matrix([
            {"risk_id": "R1", "probability": True, "impact": 10}
        ])
    with pytest.raises(ValueError, match="not boolean"):
        build_risk_exposure_matrix([], impact_medium_threshold=True)
    with pytest.raises(ValueError, match="numeric range"):
        build_risk_exposure_matrix([
            {"risk_id": "R1", "probability": 1, "impact": 1e308}
        ])
