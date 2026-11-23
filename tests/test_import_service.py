from io import BytesIO

import pytest

from ai_project_control.import_service import import_uploaded_dataset
from ai_project_control.project_store import ProjectStore


class Upload(BytesIO):
    def __init__(self, name, data):
        super().__init__(data)
        self.name = name


@pytest.fixture
def store(tmp_path):
    repository = ProjectStore(tmp_path / "pc.sqlite3")
    repository.save_dataset("workspace", "project_master", [
        {"project_id": "P1", "project_name": "Project One"}
    ])
    return repository


def test_import_csv_maps_validates_and_persists(store):
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,12\n")
    result = import_uploaded_dataset(store, "P1", "boq", upload)
    assert result["status"] == "COMMITTED"
    assert result["saved_count"] == 1
    assert store.load_dataset("P1", "boq")[0]["boq_id"] == "B1"


def test_missing_or_ambiguous_mapping_stops_without_saving(store):
    upload = Upload("boq.csv", b"Project ID,Project Code,Quantity\nP1,P1,12\n")
    result = import_uploaded_dataset(store, "P1", "boq", upload)
    assert result["status"] == "MAPPING_REQUIRED"
    assert store.load_dataset("P1", "boq") == []


def test_invalid_data_stops_without_saving(store):
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,-2\n")
    result = import_uploaded_dataset(store, "P1", "boq", upload)
    assert result["status"] == "VALIDATION_FAILED"
    assert store.load_dataset("P1", "boq") == []


def test_project_scope_mismatch_stops_without_saving(store):
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP2,B1,2\n")
    result = import_uploaded_dataset(store, "P1", "boq", upload)
    assert result["status"] == "PROJECT_SCOPE_MISMATCH"
    assert store.load_dataset("P1", "boq") == []


def test_explicit_replace_replaces_only_selected_dataset(store):
    store.save_dataset("P1", "boq", [{"project_id": "P1", "boq_id": "OLD"}])
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,NEW,2\n")
    result = import_uploaded_dataset(store, "P1", "boq", upload, mode="replace")
    assert result["status"] == "COMMITTED"
    assert [row["boq_id"] for row in store.load_dataset("P1", "boq")] == ["NEW"]


def test_unknown_dataset_and_invalid_mode_rejected(store):
    upload = Upload("boq.csv", b"Project ID,BOQ ID\nP1,B1\n")
    with pytest.raises(ValueError):
        import_uploaded_dataset(store, "P1", "unknown", upload)
    with pytest.raises(ValueError):
        import_uploaded_dataset(store, "P1", "boq", upload, mode="delete")
