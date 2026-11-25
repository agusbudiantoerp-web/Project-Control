from ai_project_control.project_recovery_intelligence import build_project_recovery_intelligence


def test_critical_project_is_prioritized_from_explicit_indicators():
    result = build_project_recovery_intelligence([
        {"project_id": "P1", "SPI": 0.75, "CPI": 0.88, "risk_score": 92,
         "delayed_activity_count": 3, "overdue_action_count": 2}
    ])
    project = result["projects"][0]
    assert project["triage_tier"] == "CRITICAL_REVIEW"
    assert result["critical_review_count"] == 1
    assert "SPI_BELOW_0_95" in project["evidence"]


def test_open_p1_action_and_adverse_change_are_included():
    result = build_project_recovery_intelligence(
        [{"project_id": "P1", "SPI": 0.98, "CPI": 1.0, "risk_score": 20,
          "delayed_activity_count": 0, "overdue_action_count": 0}],
        actions=[{"project_id": "P1", "priority": "P1", "status": "OPEN"}],
        monitoring_changes=[{"project_id": "P1", "metric": "SPI", "change": "ADVERSE_DECREASE"}],
    )
    project = result["projects"][0]
    assert project["triage_tier"] == "RECOVERY_REVIEW"
    assert project["open_p1_actions"] == 1
    assert project["adverse_monitoring_metrics"] == ["SPI"]


def test_completed_p1_action_is_not_counted():
    result = build_project_recovery_intelligence(
        [{"project_id": "P1"}],
        actions=[{"project_id": "P1", "priority": "P1", "status": "COMPLETED"}],
    )
    assert result["projects"][0]["open_p1_actions"] == 0


def test_missing_indicators_are_reported_not_zero_filled():
    result = build_project_recovery_intelligence([{"project_id": "P1"}])
    project = result["projects"][0]
    assert project["triage_tier"] == "NO_ADVERSE_SIGNAL"
    assert set(project["missing_indicators"]) == {
        "SPI", "CPI", "risk_score", "delayed_activity_count", "overdue_action_count"
    }


def test_empty_projects_returns_no_projects():
    assert build_project_recovery_intelligence([])["status"] == "NO_PROJECTS"


def test_invalid_metric_is_unassessed():
    result = build_project_recovery_intelligence([
        {"project_id": "P1", "SPI": "not numeric", "CPI": float("nan")}
    ])
    assert "SPI" in result["projects"][0]["missing_indicators"]
    assert "CPI" in result["projects"][0]["missing_indicators"]
