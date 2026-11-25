from ai_project_control.integrated_executive_report import build_integrated_executive_report


def test_report_includes_supplied_portfolio_and_decision_records():
    report = build_integrated_executive_report(
        portfolio_records=[{"project_id": "P1", "project_name": "Plant", "SPI": 0.9,
                            "CPI": 1.01, "portfolio_status": "At Risk"}],
        status_date="2026-11-23",
        director_decisions={
            "summary": {"p1_count": 1, "p2_count": 0, "data_review_count": 0, "unassessed_count": 0},
            "decisions": [{"project_name": "Plant", "priority": "P1", "evidence_points": 7,
                           "recommended_action": "Review recovery plan"}],
        },
    )
    assert "2026-11-23" in report
    assert "Plant" in report
    assert "Review recovery plan" in report
    assert "missing values are not inferred" in report


def test_report_marks_missing_sections_instead_of_fabricating():
    report = build_integrated_executive_report(
        portfolio_records=[], status_date="2026-11-23"
    )
    assert "No project records supplied" in report
    assert "No dated trend snapshots supplied" in report
    assert "No recovery assessment supplied" in report


def test_report_includes_action_and_health_snapshots():
    report = build_integrated_executive_report(
        portfolio_records=[{"project_id": "P1", "project_name": "Plant"}],
        status_date="2026-11-23",
        action_register={
            "summary": {"open_count": 1, "overdue_count": 0},
            "actions": [{"title": "Repair pump", "project_id": "P1", "owner": "PM",
                         "due_date": "2026-11-30", "priority": "P1", "status": "OPEN"}],
        },
        health_monitoring={"projects": [{
            "project_id": "P1", "status": "TREND_ASSESSED",
            "baseline_date": "2026-11-01", "latest_date": "2026-11-15",
            "changes": {"SPI": -0.1, "CPI": None, "risk_score": 5},
        }]},
        language="en",
    )
    assert "Repair pump" in report
    assert "TREND_ASSESSED" in report
    assert "INTEGRATED PORTFOLIO EXECUTIVE REPORT" in report


def test_invalid_report_date_rejected():
    import pytest
    with pytest.raises(ValueError, match="status_date"):
        build_integrated_executive_report(portfolio_records=[], status_date="invalid")
