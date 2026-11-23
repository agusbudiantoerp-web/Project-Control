import pytest

from ai_project_control.integrated_project_intelligence import build_integrated_project_intelligence


def test_integrates_performance_risk_and_director_priority():
    result = build_integrated_project_intelligence([
        {"project_id": "P1", "project_name": "Plant", "SPI": 0.80, "CPI": 0.88,
         "total_float_days": 2, "forecast_variance_pct": 12},
        {"project_id": "P2", "project_name": "Road", "SPI": 1.02, "CPI": 1.01,
         "total_float_days": 30, "forecast_variance_pct": 0},
    ])
    by_id = {row["project_id"]: row for row in result["projects"]}
    assert by_id["P1"]["priority"] == "P1"
    assert by_id["P1"]["performance_status"] == "ASSESSED"
    assert by_id["P1"]["risk_status"] in {"HIGH", "CRITICAL"}
    assert by_id["P2"]["performance_status"] == "ASSESSED"
    assert result["summary"]["project_count"] == 2


def test_missing_metrics_are_not_reported_as_green_or_assessed():
    result = build_integrated_project_intelligence([
        {"project_id": "P3", "project_name": "Incomplete"}
    ])
    row = result["projects"][0]
    assert row["performance_status"] == "INSUFFICIENT_DATA"
    assert row["risk_status"] == "DATA_INCOMPLETE"
    assert row["priority"] == "UNASSESSED"


def test_duplicate_or_missing_project_ids_rejected():
    with pytest.raises(ValueError, match="unique"):
        build_integrated_project_intelligence([
            {"project_id": "P1"}, {"project_id": "P1"}
        ])
    with pytest.raises(ValueError, match="project_id"):
        build_integrated_project_intelligence([{"project_name": "No ID"}])


def test_empty_portfolio_returns_zero_summary():
    result = build_integrated_project_intelligence([])
    assert result["projects"] == []
    assert result["summary"]["project_count"] == 0
    assert result["summary"]["critical_risk_count"] == 0
