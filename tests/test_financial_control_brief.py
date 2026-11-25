import pytest

from ai_project_control.financial_control_brief import build_financial_control_brief


def inputs():
    project = {"project_id": "P1", "BAC": 1000, "currency": "IDR"}
    progress = [{"project_id": "P1", "period": "2026-10", "planned_value": 500, "earned_value": 400}]
    costs = [{"project_id": "P1", "period": "2026-10", "actual_cost": 500}]
    return project, progress, costs


def test_financial_brief_links_evm_and_cost_scenarios():
    result = build_financial_control_brief(*inputs())
    assert result["status"] == "ASSESSED"
    assert result["evm"]["SPI"] == 0.8
    assert result["evm"]["CPI"] == 0.8
    assert result["cost_forecast"]["scenarios"]
    assert any(a["code"] == "SCHEDULE_PERFORMANCE_BELOW_PLAN" for a in result["management_alerts"])


def test_financial_brief_preserves_missing_data_as_review_required():
    project, progress, costs = inputs()
    result = build_financial_control_brief(project, [], costs)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["cost_forecast"]["status"] == "INSUFFICIENT_DATA"
    assert any(a["severity"] == "DATA_GAP" for a in result["management_alerts"])


def test_financial_brief_filters_as_of_period():
    project, progress, costs = inputs()
    progress.append({"project_id": "P1", "period": "2026-12", "planned_value": 500, "earned_value": 500})
    result = build_financial_control_brief(project, progress, costs, as_of_period="2026-10")
    assert result["evm"]["PV"] == 500


def test_project_id_is_required():
    with pytest.raises(ValueError, match="project.project_id"):
        build_financial_control_brief({}, [], [])
