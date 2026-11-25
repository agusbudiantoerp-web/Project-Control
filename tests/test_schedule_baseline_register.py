import pytest

from ai_project_control.data_quality_validation import TABLE_KEYS, validate_project_control_data
from ai_project_control.project_store import ProjectStore


def test_baseline_and_change_register_are_supported_project_datasets(tmp_path):
    store = ProjectStore(tmp_path / "baseline.sqlite3")
    store.save_dataset("P1", "project_master", [
        {"project_id": "P1", "project_name": "Baseline Test"}
    ])
    baseline = store.save_dataset("P1", "schedule_baselines", [{
        "project_id": "P1",
        "baseline_id": "BL-001",
        "baseline_name": "Approved Baseline",
        "version": 1,
        "status": "APPROVED",
        "approved_by": "Project Sponsor",
        "approved_at": "2026-11-25",
        "activities_snapshot": [
            {"activity_id": "A1", "planned_start": "2026-12-01",
             "planned_finish": "2026-12-10", "duration_days": 10}
        ],
    }])
    change = store.save_dataset("P1", "schedule_changes", [{
        "project_id": "P1",
        "change_id": "CR-001",
        "baseline_id": "BL-001",
        "description": "Additional scope",
        "cost_impact": 1500000,
        "schedule_impact_days": 3,
        "status": "PENDING",
        "date_raised": "2026-11-25",
    }])

    assert baseline["status"] == "COMMITTED"
    assert change["status"] == "COMMITTED"
    assert store.load_dataset("P1", "schedule_baselines")[0]["status"] == "APPROVED"
    assert store.load_dataset("P1", "schedule_changes")[0]["baseline_id"] == "BL-001"
    assert "schedule_baselines" in TABLE_KEYS
    assert "schedule_changes" in TABLE_KEYS


def test_baseline_and_change_records_are_isolated_by_project(tmp_path):
    store = ProjectStore(tmp_path / "baseline-isolation.sqlite3")
    for project_id in ("P1", "P2"):
        store.save_dataset(project_id, "project_master", [{"project_id": project_id}])
    store.save_dataset("P1", "schedule_baselines", [{
        "project_id": "P1", "baseline_id": "BL-1", "version": 1
    }])
    assert store.load_dataset("P2", "schedule_baselines") == []


@pytest.mark.parametrize("dataset,row", [
    ("schedule_baselines", {"project_id": "P1", "baseline_id": "BL-1", "version": -1}),
    ("schedule_changes", {"project_id": "P1", "change_id": "CR-1", "cost_impact": -1}),
    ("schedule_changes", {"project_id": "P1", "change_id": "CR-1", "schedule_impact_days": -2}),
])
def test_negative_baseline_or_change_values_are_rejected(dataset, row):
    result = validate_project_control_data({"project_master": [{"project_id": "P1"}],
                                            dataset: [row]})
    assert result["status"] == "INVALID"
    assert any(issue["code"] == "NEGATIVE_VALUE" for issue in result["issues"])


def test_change_register_rejects_unknown_project():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_changes": [{
            "project_id": "P404", "change_id": "CR-404", "cost_impact": 0
        }],
    })
    assert any(issue["code"] == "UNKNOWN_PROJECT" for issue in result["issues"])


def test_schedule_change_must_reference_existing_project_baseline():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_baselines": [{
            "project_id": "P1", "baseline_id": "BL-1", "version": 1,
        }],
        "schedule_changes": [{
            "project_id": "P1", "change_id": "CR-1", "baseline_id": "BL-MISSING",
        }],
    })
    assert any(issue["code"] == "UNKNOWN_CHANGE_BASELINE" for issue in result["issues"])


def test_baseline_snapshot_rejects_duplicate_or_missing_activity_ids():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_baselines": [{
            "project_id": "P1", "baseline_id": "BL-1", "version": 1,
            "activities_snapshot": [
                {"activity_id": "A1"}, {"activity_id": "A1"}, {"activity_name": "Missing ID"}
            ],
        }],
    })
    codes = {issue["code"] for issue in result["issues"]}
    assert "DUPLICATE_BASELINE_ACTIVITY_ID" in codes
    assert "MISSING_BASELINE_ACTIVITY_ID" in codes


def test_baseline_version_must_be_positive_integer():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_baselines": [{
            "project_id": "P1", "baseline_id": "BL-1", "version": 1.5,
        }],
    })
    assert any(issue["code"] == "INVALID_BASELINE_VERSION" for issue in result["issues"])


def test_approved_or_rejected_change_requires_decision_audit_fields():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_changes": [{
            "project_id": "P1", "change_id": "CR-1", "status": "APPROVED",
        }],
    })
    assert any(issue["code"] == "MISSING_CHANGE_DECISION_AUDIT" for issue in result["issues"])


def test_schedule_change_rejects_unknown_status():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_changes": [{
            "project_id": "P1", "change_id": "CR-1", "status": "MAYBE",
        }],
    })
    assert any(issue["code"] == "INVALID_CHANGE_STATUS" for issue in result["issues"])


def test_change_request_rejects_baseline_when_project_has_no_baseline_records():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "schedule_changes": [{
            "project_id": "P1", "change_id": "CR-1", "baseline_id": "BL-MISSING",
        }],
    })
    assert any(issue["code"] == "UNKNOWN_CHANGE_BASELINE" for issue in result["issues"])


def test_progress_activity_must_match_linked_boq_activity():
    result = validate_project_control_data({
        "project_master": [{"project_id": "P1"}],
        "activities": [
            {"project_id": "P1", "activity_id": "A1", "wbs_id": "W1"},
            {"project_id": "P1", "activity_id": "A2", "wbs_id": "W1"},
        ],
        "boq": [{
            "project_id": "P1", "boq_id": "B1", "activity_id": "A1", "wbs_id": "W1",
            "quantity": 1,
        }],
        "progress": [{
            "project_id": "P1", "activity_id": "A2", "boq_id": "B1",
            "period": "2026-11", "earned_value": 10,
        }],
    })
    assert any(issue["code"] == "PROGRESS_ACTIVITY_BOQ_MISMATCH" for issue in result["issues"])


def test_store_allows_single_dataset_change_write_then_flags_missing_baseline_in_workspace(tmp_path):
    store = ProjectStore(tmp_path / "change-link-check.sqlite3")
    store.save_dataset("P3", "project_master", [{"project_id": "P3"}])
    store.save_dataset("P3", "schedule_changes", [{
        "project_id": "P3", "change_id": "CR-3", "baseline_id": "BL-MISSING",
        "status": "PENDING",
    }])
    validation = store.validate_workspace("P3")
    assert any(issue["code"] == "UNKNOWN_CHANGE_BASELINE" for issue in validation["issues"])
