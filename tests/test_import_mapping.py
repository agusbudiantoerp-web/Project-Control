import pytest

from ai_project_control.import_mapping import map_import_rows, suggest_column_mapping


def test_suggests_unique_english_and_indonesian_headers():
    result = suggest_column_mapping("boq", ["Kode Proyek", "Kode Item", "Volume", "Harga Satuan"])
    assert result["mapping"] == {
        "project_id": "Kode Proyek",
        "boq_id": "Kode Item",
        "quantity": "Volume",
        "unit_rate": "Harga Satuan",
    }
    assert result["ready"] is True


def test_ambiguous_alias_is_not_guessed():
    result = suggest_column_mapping("project_master", ["Project ID", "Project Code"])
    assert "project_id" in result["ambiguous"]
    assert result["ready"] is False


def test_missing_required_columns_are_reported():
    result = suggest_column_mapping("activities", ["Project ID", "Description"])
    assert result["missing_required"] == ["activity_id"]
    assert result["ready"] is False


def test_map_rows_and_validate_required_fields():
    suggestion = suggest_column_mapping("boq", ["Project ID", "BOQ ID", "Quantity"])
    result = map_import_rows("boq", [
        {"Project ID": "P1", "BOQ ID": "B1", "Quantity": 12}
    ], suggestion["mapping"])
    assert result["row_count"] == 1
    assert result["rows"][0]["project_id"] == "P1"
    assert result["ready_for_analysis"] is True


def test_invalid_rows_are_not_marked_ready():
    result = map_import_rows("boq", [
        {"Project ID": "P1", "BOQ ID": "B1", "Quantity": -5}
    ], {"project_id": "Project ID", "boq_id": "BOQ ID", "quantity": "Quantity"})
    assert result["ready_for_analysis"] is False
    assert result["validation"]["status"] == "INVALID"


def test_rejects_unknown_table_target_and_bad_rows():
    with pytest.raises(ValueError):
        suggest_column_mapping("unknown", ["ID"])
    with pytest.raises(ValueError):
        map_import_rows("boq", [], {"made_up_field": "X"})
    with pytest.raises(TypeError):
        map_import_rows("boq", ["not a row"], {})


def test_normalizes_underscores_and_repeated_spaces():
    result = suggest_column_mapping("activities", ["project__id", "activity-code"])
    assert result["mapping"]["project_id"] == "project__id"
    assert result["mapping"]["activity_id"] == "activity-code"
