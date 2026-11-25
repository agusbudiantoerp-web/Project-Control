import pytest

from ai_project_control.project_store import ProjectStore


def seed_project(store, project_id="P1"):
    return store.save_dataset(project_id, "project_master", [{"project_id": project_id, "project_name": "Project"}])


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


def test_in_memory_store_persists_across_operation_connections():
    memory_store = ProjectStore(":memory:")
    seed_project(memory_store)
    memory_store.save_dataset("P1", "boq", [
        {"project_id": "P1", "boq_id": "B1", "quantity": 7}
    ])
    assert memory_store.load_dataset("P1", "boq")[0]["quantity"] == 7


def test_store_connections_are_closed_after_operations(tmp_path):
    store = ProjectStore(tmp_path / "closed.sqlite3")
    seed_project(store)
    assert store.list_project_ids() == ["P1"]
    assert store._memory_keeper is None


def test_rejects_database_with_newer_schema_version(tmp_path):
    import sqlite3

    database = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO store_metadata(key, value) VALUES ('schema_version', '999')"
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="newer than this application"):
        ProjectStore(database)

    check = sqlite3.connect(database)
    tables = {
        row[0] for row in check.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    check.close()
    assert "project_records" not in tables
    assert "import_events" not in tables


def test_in_memory_store_can_release_keeper_connection():
    import sqlite3

    memory_store = ProjectStore(":memory:")
    seed_project(memory_store)
    keeper = memory_store._memory_keeper
    assert keeper is not None
    memory_store.close()
    assert memory_store._memory_keeper is None
    with pytest.raises(sqlite3.ProgrammingError):
        keeper.execute("SELECT 1")
    with pytest.raises(RuntimeError, match="ProjectStore is closed"):
        memory_store.list_project_ids()


def test_project_store_context_manager_closes_in_memory_database():
    with ProjectStore(":memory:") as memory_store:
        seed_project(memory_store)
        assert memory_store.list_project_ids() == ["P1"]
    assert memory_store._memory_keeper is None


def test_rejects_older_schema_without_claiming_migration(tmp_path):
    import sqlite3

    database = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO store_metadata(key, value) VALUES ('schema_version', '0')"
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="older than this application"):
        ProjectStore(database)


def test_multi_dataset_save_is_atomic_when_one_dataset_is_invalid(tmp_path):
    database = tmp_path / "atomic.sqlite3"
    store = ProjectStore(database)
    seed_project(store)
    with pytest.raises(ValueError, match="validation failed|Multi-dataset validation failed"):
        store.save_datasets("P1", {
            "boq": [{
                "project_id": "P1", "boq_id": "B1", "quantity": 10,
            }],
            "risk": [{
                "project_id": "P1", "risk_id": "R1", "probability": 2, "impact": 100,
            }],
        })
    assert store.load_dataset("P1", "boq") == []
    assert store.load_dataset("P1", "risk") == []


def test_multi_dataset_save_commits_new_project_and_related_data_together(tmp_path):
    store = ProjectStore(tmp_path / "atomic-new.sqlite3")
    result = store.save_datasets("P2", {
        "project_master": [{
            "project_id": "P2", "project_name": "XER Import", "currency": "IDR",
        }],
        "wbs": [{
            "project_id": "P2", "wbs_id": "W1", "wbs_name": "Civil",
        }],
        "activities": [{
            "project_id": "P2", "activity_id": "A1", "duration_days": 5,
            "predecessors": [],
        }],
    })
    assert set(result) == {"project_master", "wbs", "activities"}
    assert store.list_project_ids() == ["P2"]
    assert len(store.load_dataset("P2", "wbs")) == 1
    assert len(store.load_dataset("P2", "activities")) == 1


def test_multi_dataset_database_failure_rolls_back_entire_batch(tmp_path):
    import sqlite3

    database = tmp_path / "atomic-rollback.sqlite3"
    store = ProjectStore(database)
    connection = sqlite3.connect(database)
    connection.execute("""
        CREATE TRIGGER fail_activity_insert
        BEFORE INSERT ON project_records
        WHEN NEW.dataset = 'activities'
        BEGIN
            SELECT RAISE(ABORT, 'forced activity insert failure');
        END;
    """)
    connection.commit()
    connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="forced activity insert failure"):
        store.save_datasets("P3", {
            "project_master": [{
                "project_id": "P3", "project_name": "Atomic Test", "currency": "IDR",
            }],
            "wbs": [{"project_id": "P3", "wbs_id": "W1"}],
            "activities": [{
                "project_id": "P3", "activity_id": "A1", "duration_days": 1,
            }],
        })
    assert store.load_dataset("P3", "project_master") == []
    assert store.load_dataset("P3", "wbs") == []
    assert store.load_dataset("P3", "activities") == []


def test_workspace_metadata_persists_and_protects_schema_version(tmp_path):
    store = ProjectStore(tmp_path / "metadata.sqlite3")
    assert store.get_metadata("telegram_update_offset:123") is None
    store.set_metadata("telegram_update_offset:123", "42")
    assert store.get_metadata("telegram_update_offset:123") == "42"
    with pytest.raises(ValueError, match="reserved"):
        store.set_metadata("schema_version", "999")
