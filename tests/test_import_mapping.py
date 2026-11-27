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


def test_maps_portfolio_health_snapshots_from_english_and_indonesian_headers():
    result = suggest_column_mapping(
        "portfolio_snapshots",
        ["Kode Proyek", "Tanggal Snapshot", "Schedule Performance Index",
         "Cost Performance Index", "Skor Risiko"],
    )
    assert result["ready"] is True
    assert result["mapping"] == {
        "project_id": "Kode Proyek",
        "snapshot_date": "Tanggal Snapshot",
        "SPI": "Schedule Performance Index",
        "CPI": "Cost Performance Index",
        "risk_score": "Skor Risiko",
    }


def test_rejects_invalid_portfolio_snapshot_date_and_risk_score():
    result = map_import_rows(
        "portfolio_snapshots",
        [{"Project ID": "P1", "Snapshot Date": "yesterday", "Risk Score": 120}],
        {"project_id": "Project ID", "snapshot_date": "Snapshot Date", "risk_score": "Risk Score"},
    )
    codes = {issue["code"] for issue in result["validation"]["issues"]}
    assert "INVALID_SNAPSHOT_DATE" in codes
    assert "RISK_SCORE_OUT_OF_RANGE" in codes


def test_rejects_one_source_column_mapped_to_multiple_targets():
    with pytest.raises(ValueError, match="cannot be mapped to multiple"):
        map_import_rows(
            "boq",
            [{"Project ID": "P1", "Shared": "B1"}],
            {"project_id": "Project ID", "boq_id": "Shared", "quantity": "Shared"},
        )


def test_rejects_empty_source_column_mapping():
    with pytest.raises(ValueError, match="non-empty column name"):
        map_import_rows("boq", [], {"project_id": ""})


def test_maps_project_evm_record_modes_from_master_import():
    result = suggest_column_mapping("project_master", [
        "Project ID", "Progress Mode", "Actual Cost Mode"
    ])
    assert result["mapping"]["progress_record_mode"] == "Progress Mode"
    assert result["mapping"]["actual_cost_record_mode"] == "Actual Cost Mode"
    mapped = map_import_rows("project_master", [{
        "Project ID": "P1",
        "Progress Mode": "cumulative_snapshot",
        "Actual Cost Mode": "period_delta",
    }], result["mapping"])
    assert mapped["rows"][0]["progress_record_mode"] == "cumulative_snapshot"
    assert mapped["rows"][0]["actual_cost_record_mode"] == "period_delta"


def test_maps_wbs_activity_and_boq_crosswalk_fields():
    boq = suggest_column_mapping("boq", [
        "Project ID", "BOQ ID", "WBS ID", "Activity Code", "Qty"
    ])
    assert boq["mapping"]["wbs_id"] == "WBS ID"
    assert boq["mapping"]["activity_id"] == "Activity Code"

    activities = suggest_column_mapping("activities", [
        "Project ID", "Activity ID", "WBS Code", "Predecessors", "Duration"
    ])
    assert activities["mapping"]["wbs_id"] == "WBS Code"
    assert activities["mapping"]["predecessor_ids"] == "Predecessors"

    progress = suggest_column_mapping("progress", [
        "Project ID", "Activity ID", "BOQ ID", "Period", "EV"
    ])
    assert progress["mapping"]["boq_id"] == "BOQ ID"

    costs = suggest_column_mapping("actual_cost", [
        "Project ID", "Period", "Cost Code", "AC", "BOQ ID", "WBS ID"
    ])
    assert costs["mapping"]["boq_id"] == "BOQ ID"
    assert costs["mapping"]["wbs_id"] == "WBS ID"
