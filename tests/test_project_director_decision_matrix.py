"""Tests for project director decision matrix."""
from ai_project_control.project_director_decision_matrix import build_decision_matrix


def test_critical_project_is_p1_and_ranked_first():
    result = build_decision_matrix([
        {"project_id": "stable", "SPI": 1.0, "CPI": 1.0, "risk_score": 10},
        {"project_id": "critical", "SPI": 0.8, "CPI": 0.9, "risk_score": 80},
    ])
    assert result["decisions"][0]["project_id"] == "critical"
    assert result["decisions"][0]["priority"] == "P1"


def test_missing_metrics_are_not_classified_as_stable():
    result = build_decision_matrix([
        {"project_id": "partial", "SPI": 1.0, "CPI": 1.0},
        {"project_id": "empty"},
    ])
    rows = {row["project_id"]: row for row in result["decisions"]}
    assert rows["partial"]["priority"] == "DATA_REVIEW"
    assert rows["empty"]["priority"] == "UNASSESSED"


def test_resource_overload_adds_evidence_point():
    result = build_decision_matrix([
        {"project_id": "A", "SPI": 1.0, "CPI": 1.0, "risk_score": 20,
         "overloaded_resource_days": 4}
    ])
    assert result["decisions"][0]["evidence_points"] == 1


def test_non_finite_values_are_missing():
    result = build_decision_matrix([
        {"project_id": "A", "SPI": float("nan"), "CPI": float("inf"), "risk_score": 90}
    ])
    row = result["decisions"][0]
    assert row["SPI"] is None
    assert row["CPI"] is None
    assert "SPI" in row["data_gaps"]
    assert "CPI" in row["data_gaps"]


def test_empty_input_returns_zero_summary():
    result = build_decision_matrix([])
    assert result["summary"]["project_count"] == 0
    assert result["decisions"] == []
