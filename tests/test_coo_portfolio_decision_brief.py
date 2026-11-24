import pytest

from ai_project_control.coo_portfolio_decision_brief import build_coo_portfolio_decision_brief


def test_coo_brief_flags_p1_overdue_actions_and_resource_conflicts():
    result = build_coo_portfolio_decision_brief(
        {
            "status": "ASSESSED", "project_count": 1,
            "projects": [{
                "project_id": "P1", "project_name": "Mine A", "priority": "P1",
                "SPI": .8, "CPI": .9, "currency": "IDR",
                "delayed_activity_count": 2, "resource_overloaded_count": 1,
            }],
        },
        {
            "shared_resource_conflict_count": 1,
            "shared_resource_conflicts": [{"resource_id": "EX-01"}],
            "top_risks": [{"project_id": "P1", "risk_id": "R1"}],
            "expected_exposure_by_currency": {"IDR": 50},
            "risk_count_unassessed": 1,
            "unassessed_resources": [],
        },
        {"actions": [], "summary": {"overdue_count": 2, "blocked_count": 1, "action_count": 3}},
        as_of_date="2026-11-24",
    )
    assert result["projects_requiring_review"] == 1
    assert "P1_PRIORITY" in result["projects_for_review"][0]["flags"]
    assert "SCHEDULE_DELAY" in result["projects_for_review"][0]["flags"]
    assert len(result["recommended_management_reviews"]) >= 4
    assert result["risk_exposure_by_currency"] == {"IDR": 50}


def test_coo_brief_does_not_mark_missing_metrics_green():
    result = build_coo_portfolio_decision_brief(
        {"project_count": 1, "projects": [{"project_id": "P2", "priority": "UNASSESSED"}]},
        {"shared_resource_conflicts": [], "top_risks": [], "risk_count_unassessed": 0},
        {"actions": [], "summary": {}},
    )
    assert result["projects_for_review"][0]["flags"] == ["INSUFFICIENT_EVM_DATA"]


def test_coo_brief_empty_portfolio_and_input_validation():
    result = build_coo_portfolio_decision_brief(
        {"project_count": 0, "projects": []},
        {"shared_resource_conflicts": [], "top_risks": [], "risk_count_unassessed": 0},
        {"actions": [], "summary": {}},
    )
    assert result["status"] == "NO_PROJECTS"
    with pytest.raises(TypeError):
        build_coo_portfolio_decision_brief([], {}, {})
    with pytest.raises(ValueError, match="as_of_date"):
        build_coo_portfolio_decision_brief({}, {}, {}, as_of_date="bad-date")
