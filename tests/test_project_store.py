import pytest

from ai_project_control.project_store import ProjectStore


def seed_project(store, project_id="P1"):
    return store.save_dataset("workspace", "project_master", [{"project_id": project_id, "project_name": "Project"}])


@pytest.fixture
def store(tmp_path):
    return ProjectStore(tmp_path / "project_control.sqlite3")


def test_saves_and_loads_project_scoped_records(store):
    seed_project(store)
    result = store.save_dataset("P1", "boq", [
        {"project_id": "P1", "boq_id": "B1", "quantity": 5, "unit_rate": 10}
    ])
    assert result["saved_count"] == 1
    assert store.load_dataset("P1", "boq")[0]["boq_id"] == "B1"


def test_rejects_import_for_unknown_project(store):
    with pytest.raises(ValueError, match="must exist"):
        store.save_dataset("P404", "boq", [{"project_id": "P404", "boq_id": "B1"}])


def test_rejects_cross_project_rows(store):
    seed_project(store)
    with pytest.raises(ValueError, match="not 'P1'"):
        store.save_dataset("P1", "boq", [{"project_id": "P2", "boq_id": "B1"}])


def test_upsert_updates_existing_key(store):
    seed_project(store)
    store.save_dataset("P1", "boq", [{"project_id": "P1", "boq_id": "B1", "quantity": 1}])
    store.save_dataset("P1", "boq", [{"project_id": "P1", "boq_id": "B1", "quantity": 2}])
    rows = store.load_dataset("P1", "boq")
    assert len(rows) == 1
    assert rows[0]["quantity"] == 2


def test_replace_removes_old_records_for_that_dataset_only(store):
    seed_project(store)
    store.save_dataset("P1", "boq", [
        {"project_id": "P1", "boq_id": "B1"},
        {"project_id": "P1", "boq_id": "B2"},
    ])
    store.save_dataset("P1", "boq", [{"project_id": "P1", "boq_id": "B3"}], mode="replace")
    assert [r["boq_id"] for r in store.load_dataset("P1", "boq")] == ["B3"]


def test_failed_validation_does_not_persist_partial_rows(store):
    seed_project(store)
    with pytest.raises(ValueError, match="validation failed"):
        store.save_dataset("P1", "boq", [
            {"project_id": "P1", "boq_id": "B1", "quantity": -3}
        ])
    assert store.load_dataset("P1", "boq") == []


def test_import_history_is_recorded(store):
    seed_project(store)
    result = store.save_dataset("P1", "boq", [{"project_id": "P1", "boq_id": "B1"}])
    history = store.import_history("P1")
    assert history[0]["event_id"] == result["event_id"]
    assert history[0]["status"] == "COMMITTED"


def test_project_workspaces_are_isolated(store):
    seed_project(store, "P1")
    seed_project(store, "P2")
    store.save_dataset("P1", "risk", [{"project_id": "P1", "risk_id": "R1"}])
    assert store.load_dataset("P2", "risk") == []


def test_rejects_duplicate_keys_in_same_import(store):
    seed_project(store)
    with pytest.raises(ValueError, match="Duplicate record key"):
        store.save_dataset("P1", "boq", [
            {"project_id": "P1", "boq_id": "B1"},
            {"project_id": "P1", "boq_id": "B1"},
        ])
