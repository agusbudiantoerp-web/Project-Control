import pytest

from ai_project_control.schedule_baseline_service import (
    approve_schedule_baseline,
    compare_schedule_to_baseline,
    create_schedule_baseline,
)


def sample_activities():
    return [
        {"activity_id": "A1", "wbs_id": "W1", "planned_start": "2026-12-01",
         "planned_finish": "2026-12-10", "duration_days": 10, "predecessors": []},
        {"activity_id": "A2", "wbs_id": "W1", "planned_start": "2026-12-11",
         "planned_finish": "2026-12-20", "duration_days": 10, "predecessors": ["A1"]},
    ]


def test_baseline_is_a_snapshot_not_a_live_reference():
    activities = sample_activities()
    baseline = create_schedule_baseline("P1", "BL-1", activities)
    activities[0]["planned_finish"] = "2026-12-31"
    assert baseline["activities_snapshot"][0]["planned_finish"] == "2026-12-10"
    assert baseline["status"] == "DRAFT"


def test_approval_requires_named_approver_and_only_draft_can_be_approved():
    baseline = create_schedule_baseline("P1", "BL-1", sample_activities())
    with pytest.raises(ValueError, match="approved_by"):
        approve_schedule_baseline(baseline, " ")
    approved = approve_schedule_baseline(baseline, "Project Sponsor",
                                         approved_at="2026-11-25T10:00:00+00:00")
    assert approved["status"] == "APPROVED"
    assert approved["approved_by"] == "Project Sponsor"
    assert baseline["status"] == "DRAFT"
    with pytest.raises(ValueError, match="only a DRAFT"):
        approve_schedule_baseline(approved, "Another Approver")


def test_baseline_comparison_detects_additions_removals_and_changes():
    baseline = create_schedule_baseline("P1", "BL-1", sample_activities())
    current = [
        {"activity_id": "A1", "wbs_id": "W2", "planned_start": "2026-12-02",
         "planned_finish": "2026-12-12", "duration_days": 11, "predecessors": []},
        {"activity_id": "A3", "planned_start": "2026-12-21"},
    ]
    result = compare_schedule_to_baseline(baseline, current)
    assert result["status"] == "VARIANCE_DETECTED"
    assert result["added_activity_ids"] == ["A3"]
    assert result["removed_activity_ids"] == ["A2"]
    assert result["changed_count"] == 1
    assert set(result["changed_activities"][0]["differences"]) == {
        "wbs_id", "planned_start", "planned_finish", "duration_days"
    }


def test_unchanged_schedule_returns_unchanged_status():
    activities = sample_activities()
    baseline = create_schedule_baseline("P1", "BL-1", activities)
    result = compare_schedule_to_baseline(baseline, activities)
    assert result["status"] == "UNCHANGED"
    assert result["changed_count"] == 0


def test_baseline_rejects_missing_or_duplicate_activity_ids():
    with pytest.raises(ValueError, match="without activities"):
        create_schedule_baseline("P1", "BL-1", [])
    with pytest.raises(ValueError, match="missing activity_id"):
        create_schedule_baseline("P1", "BL-1", [{"activity_name": "No ID"}])
    with pytest.raises(ValueError, match="duplicate activity_id"):
        create_schedule_baseline("P1", "BL-1", [
            {"activity_id": "A1"}, {"activity_id": "A1"}
        ])


def test_baseline_rejects_invalid_identity_and_version():
    with pytest.raises(ValueError, match="project_id and baseline_id"):
        create_schedule_baseline("", "BL-1", sample_activities())
    for version in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match="positive integer"):
            create_schedule_baseline("P1", "BL-1", sample_activities(), version=version)
