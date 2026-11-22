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
