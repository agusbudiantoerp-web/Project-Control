import pandas as pd

import core


def test_default_project_template_to_report_and_backup_workflow(tmp_path, monkeypatch):
    """Exercise a complete synthetic project through validation, persistence, exports and restore."""
    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    monkeypatch.setattr(core, "DB_PATH", tmp_path / "workflow.db")

    datasets = {
        name: pd.DataFrame([row], columns=columns)
        for name, (columns, row) in core.TEMPLATES.items()
    }

    assert core.validate_project_datasets(datasets) == {}

    for name, frame in datasets.items():
        core.save_dataset("PRJ-001", name, frame)

    loaded = {name: core.load_dataset("PRJ-001", name) for name in core.TEMPLATES}
    assert set(core.list_datasets("PRJ-001")) == set(core.TEMPLATES)
    assert core.validate_project_datasets(loaded) == {}

    workbook = core.export_workbook(loaded, {"Workflow Check": pd.DataFrame([{"status": "PASS"}])})
    assert workbook[:2] == b"PK"

    pdf = core.generate_pdf_report(
        "PRJ-001", "Demo Construction Project", "2026-03-31",
        loaded, {"Workflow Check": pd.DataFrame([{"status": "PASS"}])},
        {"Dataset count": len(loaded)},
    )
    assert pdf.startswith(b"%PDF")

    backup = core.export_project_backup("PRJ-001")
    restored = core.import_project_backup("PRJ-RESTORED", backup)
    assert set(restored) == set(core.TEMPLATES)

    restored_master = core.load_dataset("PRJ-RESTORED", "project_master.csv")
    assert restored_master.iloc[0]["project_name"] == "Demo Construction Project"


def test_backup_rejects_non_object_manifest_without_modifying_destination(tmp_path, monkeypatch):
    import json
    import zipfile
    from io import BytesIO

    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    monkeypatch.setattr(core, "DB_PATH", tmp_path / "backup_validation.db")
    original = pd.DataFrame([{"project_id": "KEEP", "project_name": "Keep Me",
                              "planned_start": "2026-01-01", "planned_finish": "2026-12-31",
                              "status_date": "2026-03-31", "currency": "IDR"}])
    core.save_dataset("DEST", "project_master.csv", original)
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(["not", "an", "object"]))
    try:
        core.import_project_backup("DEST", stream.getvalue())
    except ValueError as exc:
        assert "manifest" in str(exc).lower() or "invalid" in str(exc).lower()
    else:
        raise AssertionError("A non-object manifest must be rejected")
    restored = core.load_dataset("DEST", "project_master.csv")
    assert restored.iloc[0]["project_name"] == "Keep Me"


def test_backup_rejects_unlisted_archive_entries(tmp_path, monkeypatch):
    import json
    import zipfile
    from io import BytesIO

    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    monkeypatch.setattr(core, "DB_PATH", tmp_path / "backup_extra_entry.db")
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps({
            "format": "AIProjectControlBackup", "version": 1, "datasets": []
        }))
        archive.writestr("../unexpected.txt", "unexpected")
    try:
        core.import_project_backup("DEST", stream.getvalue())
    except ValueError as exc:
        assert "unexpected" in str(exc).lower() or "entries" in str(exc).lower()
    else:
        raise AssertionError("Unlisted archive members must be rejected")
