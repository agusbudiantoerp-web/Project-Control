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
    repository.save_dataset("P1", "project_master", [
        {"project_id": "P1", "project_name": "Project One"}
    ])
    return repository


def test_import_csv_maps_validates_and_persists(store):
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,12\n")
    result = import_uploaded_dataset(store, "P1", "boq", upload)
    assert result["status"] == "COMMITTED"
    assert result["saved_count"] == 1
    assert store.load_dataset("P1", "boq")[0]["boq_id"] == "B1"


def test_import_rewinds_upload_stream_before_parsing(store):
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,12\n")
    upload.seek(10)
    result = import_uploaded_dataset(store, "P1", "boq", upload)
    assert result["status"] == "COMMITTED"
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


def test_import_uses_explicit_selected_xlsx_worksheet(store):
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    first = workbook.active
    first.title = "Instructions"
    first.append(["Notes"])
    first.append(["Do not import this sheet"])
    selected = workbook.create_sheet("BOQ Data")
    selected.append(["Project ID", "BOQ ID", "Quantity"])
    selected.append(["P1", "B-SELECTED", 15])
    stream = BytesIO()
    workbook.save(stream)

    upload = Upload("multi-sheet.xlsx", stream.getvalue())
    result = import_uploaded_dataset(
        store, "P1", "boq", upload, sheet_name="BOQ Data"
    )
    assert result["status"] == "COMMITTED"
    saved = store.load_dataset("P1", "boq")
    assert [row["boq_id"] for row in saved] == ["B-SELECTED"]


def test_import_rejects_source_column_reused_for_multiple_fields(store):
    upload = Upload("boq.csv", b"Project ID,Shared\\nP1,B1\\n")
    with pytest.raises(ValueError, match="cannot be mapped to multiple"):
        import_uploaded_dataset(
            store, "P1", "boq", upload,
            mapping={
                "project_id": "Project ID",
                "boq_id": "Shared",
                "quantity": "Shared",
            },
        )
    assert store.load_dataset("P1", "boq") == []
