import pytest
from ai_project_control.project_store import ProjectStore
from ai_project_control.workspace_service import build_workspace_overview


def test_workspace_overview_reads_inventory_validation_and_history(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1",
        "project_name": "Plant Expansion",
        "SPI": 0.92,
        "CPI": 1.01,
        "currency": "IDR",
        "bac": 1250000,
    }])
    store.save_dataset("P1", "boq", [{
        "project_id": "P1",
        "boq_id": "B-01",
        "quantity": 10,
        "unit_rate": 250,
    }])

    result = build_workspace_overview(db, "P1")
    assert result["project"]["project_name"] == "Plant Expansion"
    assert result["dataset_counts"]["boq"] == 1
    assert result["dataset_counts"]["project_master"] == 1
    assert result["total_records"] == 2
    assert result["scorecard"]["projects"][0]["status"] == "ASSESSED"
    assert result["scorecard"]["projects"][0]["schedule_state"] == "RED"
    assert len(result["recent_imports"]) == 2
    assert result["evm"]["status"] == "INSUFFICIENT_DATA"
    assert result["evm"]["PV"] is None
    assert result["schedule"]["status"] == "NO_ACTIVITIES"
    assert result["schedule_forecast"]["status"] == "NO_ACTIVITIES"


def test_missing_project_is_not_reported_as_empty_success(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    ProjectStore(db)
    try:
        build_workspace_overview(db, "MISSING")
    except ValueError as exc:
        assert "was not found" in str(exc)
    else:
        raise AssertionError("Missing project must raise ValueError")


def test_missing_spi_cpi_remains_insufficient_data(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P2", "project_master", [{"project_id": "P2", "project_name": "New project"}])
    result = build_workspace_overview(db, "P2")
    assert result["scorecard"]["projects"][0]["status"] == "INSUFFICIENT_DATA"
    assert result["scorecard"]["summary"]["insufficient_data_count"] == 1


def test_workspace_overview_compares_current_schedule_with_latest_approved_baseline(tmp_path):
    db = tmp_path / "baseline-workspace.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P3", "project_master", [{"project_id": "P3", "project_name": "Baseline Project"}])
    store.save_dataset("P3", "activities", [{
        "project_id": "P3", "activity_id": "A1", "planned_start": "2026-12-02",
        "planned_finish": "2026-12-12", "duration_days": 11,
    }])
    store.save_dataset("P3", "schedule_baselines", [{
        "project_id": "P3", "baseline_id": "BL-1", "version": 1,
        "status": "APPROVED", "approved_at": "2026-11-25T10:00:00+00:00",
        "activities_snapshot": [{
            "activity_id": "A1", "planned_start": "2026-12-01",
            "planned_finish": "2026-12-10", "duration_days": 10,
        }],
    }])

    result = build_workspace_overview(db, "P3")
    assert result["active_schedule_baseline"]["baseline_id"] == "BL-1"
    assert result["schedule_variance"]["status"] == "VARIANCE_DETECTED"
    assert result["schedule_variance"]["changed_count"] == 1


def test_workspace_without_approved_baseline_reports_missing_baseline(tmp_path):
    db = tmp_path / "no-approved-baseline.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P4", "project_master", [{"project_id": "P4"}])
    store.save_dataset("P4", "schedule_baselines", [{
        "project_id": "P4", "baseline_id": "BL-DRAFT", "version": 1,
        "status": "DRAFT", "activities_snapshot": [],
    }])
    result = build_workspace_overview(db, "P4")
    assert result["active_schedule_baseline"] is None
    assert result["schedule_variance"]["status"] == "NO_APPROVED_BASELINE"


def test_workspace_uses_project_configured_cumulative_evm_record_modes(tmp_path):
    db = tmp_path / "evm-snapshot-workspace.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P5", "project_master", [{
        "project_id": "P5", "project_name": "Snapshot EVM", "currency": "IDR",
        "bac": 2000, "progress_record_mode": "cumulative_snapshot",
        "actual_cost_record_mode": "cumulative_snapshot",
    }])
    store.save_dataset("P5", "progress", [
        {"project_id": "P5", "activity_id": "A1", "period": "2026-01",
         "planned_value": 100, "earned_value": 80},
        {"project_id": "P5", "activity_id": "A1", "period": "2026-02",
         "planned_value": 150, "earned_value": 120},
    ])
    store.save_dataset("P5", "actual_cost", [
        {"project_id": "P5", "period": "2026-01", "cost_code": "C1", "actual_cost": 90},
        {"project_id": "P5", "period": "2026-02", "cost_code": "C1", "actual_cost": 140},
    ])

    result = build_workspace_overview(db, "P5")
    assert result["evm"]["PV"] == 150
    assert result["evm"]["EV"] == 120
    assert result["evm"]["AC"] == 140
    assert result["evm"]["source_record_counts"] == {"progress": 1, "actual_cost": 1}


def test_workspace_rejects_unsupported_project_evm_record_mode(tmp_path):
    db = tmp_path / "invalid-evm-mode.sqlite3"
    store = ProjectStore(db)
    with pytest.raises(ValueError, match="INVALID_EVM_RECORD_MODE"):
        store.save_dataset("P6", "project_master", [{
            "project_id": "P6", "progress_record_mode": "guess_from_data",
        }])
