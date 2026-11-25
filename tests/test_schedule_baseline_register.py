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
