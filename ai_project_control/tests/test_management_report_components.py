import pandas as pd
import pytest

from core import calculate_change_impact, calculate_milestones


def test_change_control_updates_revised_budget_only_for_approved_changes():
    changes = pd.DataFrame([
        {"change_id": "CR-01", "cost_impact": 120, "schedule_impact_days": 5, "status": "Approved"},
        {"change_id": "CR-02", "cost_impact": 80, "schedule_impact_days": 3, "status": "Pending"},
        {"change_id": "CR-03", "cost_impact": 40, "schedule_impact_days": 2, "status": "Rejected"},
    ])

    frame, stats = calculate_change_impact(changes, 1000)

    assert stats["approved_cost_impact"] == pytest.approx(120)
    assert stats["approved_schedule_days"] == pytest.approx(5)
    assert stats["revised_budget"] == pytest.approx(1120)
    assert stats["pending_count"] == 1
    assert stats["pending_cost_exposure"] == pytest.approx(80)
    assert frame.set_index("change_id").loc["CR-02", "control_class"] == "Pending decision"


def test_milestone_forecast_slippage_and_completion_are_reported():
    milestones = pd.DataFrame([
        {"milestone_id": "M1", "planned_date": "2026-03-01", "forecast_date": "2026-03-06", "actual_date": None, "status": "At Risk"},
        {"milestone_id": "M2", "planned_date": "2026-03-02", "forecast_date": None, "actual_date": "2026-03-02", "status": "Completed"},
        {"milestone_id": "M3", "planned_date": "2026-03-05", "forecast_date": "2026-03-05", "actual_date": None, "status": "On Track"},
        {"milestone_id": "M4", "planned_date": "2026-03-02", "forecast_date": "2026-03-03", "actual_date": None, "status": "Overdue"},
    ])

    frame, stats = calculate_milestones(milestones, "2026-03-04")

    assert stats == {"total": 4, "completed": 1, "delayed": 2, "at_risk": 2}
    assert frame.set_index("milestone_id").loc["M1", "calculated_status"] == "At Risk"
    assert frame.set_index("milestone_id").loc["M2", "calculated_status"] == "Completed"
    assert frame.set_index("milestone_id").loc["M3", "calculated_status"] == "On Track"
    assert frame.set_index("milestone_id").loc["M4", "calculated_status"] == "Overdue"
