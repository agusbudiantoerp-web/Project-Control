import pytest

from ai_project_control.recovery_execution import (
    RecoveryPlanStore, create_recovery_plan, evaluate_recovery_plan,
)


def sample_plan(**overrides):
    args = {
        "project_id": "P-01", "title": "Schedule recovery", "owner": "PM",
        "start_date": "2026-11-01", "target_finish": "2026-12-01",
        "baseline_finish": "2026-11-20",
        "milestones": [
            {"milestone_id": "M1", "name": "Approve resequencing", "due_date": "2026-11-10", "target_percent": 100},
            {"milestone_id": "M2", "name": "Complete recovery works", "due_date": "2026-11-30", "target_percent": 100},
        ],
    }
    args.update(overrides)
    return create_recovery_plan(**args)


def test_create_plan_normalizes_and_sorts_milestones():
    plan = sample_plan()
    assert plan["status"] == "ACTIVE"
    assert [m["milestone_id"] for m in plan["milestones"]] == ["M1", "M2"]


def test_rejects_invalid_dates_and_milestone_percent():
    with pytest.raises(ValueError):
        sample_plan(target_finish="2026-10-01")
    with pytest.raises(ValueError):
        sample_plan(milestones=[{"name": "Bad", "due_date": "2026-11-10", "target_percent": 101}])


def test_evaluate_flags_overdue_incomplete_milestone():
    result = evaluate_recovery_plan(sample_plan(), as_of="2026-11-23")
    assert result["overdue_count"] == 1
    assert result["status"] == "OVERDUE_MILESTONES"


def test_evaluate_reports_average_progress_gap():
    plan = sample_plan()
    plan["milestones"][0]["actual_percent"] = 100
    result = evaluate_recovery_plan(plan, as_of="2026-11-05")
    assert result["average_actual_percent"] == 50
    assert result["progress_gap_percentage_points"] == 50


def test_store_persists_updates_and_audit_events(tmp_path):
    store = RecoveryPlanStore(tmp_path / "recovery.sqlite3")
    plan = store.create(**{
        "project_id": "P-01", "title": "Recovery", "owner": "PM",
        "start_date": "2026-11-01", "target_finish": "2026-12-01",
        "baseline_finish": "2026-11-20",
        "milestones": [{"milestone_id": "M1", "name": "Milestone", "due_date": "2026-11-20", "target_percent": 100}],
    })
    updated = store.update_milestone(plan["plan_id"], "M1", actual_percent=40,
                                      status="IN_PROGRESS", changed_by="PM", note="Evidence reviewed")
    loaded = store.get(plan["plan_id"])
    assert loaded["plan"]["milestones"][0]["actual_percent"] == 40
    assert len(loaded["events"]) == 1
    assert updated["event"]["changed_by"] == "PM"


def test_completed_requires_full_progress_and_progress_cannot_decrease(tmp_path):
    store = RecoveryPlanStore(tmp_path / "recovery.sqlite3")
    plan = store.create(**{
        "project_id": "P-01", "title": "Recovery", "owner": "PM",
        "start_date": "2026-11-01", "target_finish": "2026-12-01",
        "baseline_finish": "2026-11-20",
        "milestones": [{"milestone_id": "M1", "name": "Milestone", "due_date": "2026-11-20", "target_percent": 100}],
    })
    store.update_milestone(plan["plan_id"], "M1", actual_percent=100, status="COMPLETED", changed_by="PM")
    with pytest.raises(ValueError):
        store.update_milestone(plan["plan_id"], "M1", actual_percent=90, status="IN_PROGRESS", changed_by="PM")
    with pytest.raises(ValueError):
        store.update_milestone(plan["plan_id"], "M1", actual_percent=50, status="COMPLETED", changed_by="PM")
