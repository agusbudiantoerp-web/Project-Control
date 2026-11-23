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
