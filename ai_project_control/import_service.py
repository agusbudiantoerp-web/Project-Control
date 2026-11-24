"""Orchestrate upload parsing, mapping, validation and SQLite persistence.

No implicit replace is performed. Callers must explicitly request replace mode.
"""
from __future__ import annotations

from typing import Any

from .data_quality_validation import TABLE_KEYS
from .project_store import ProjectStore
from .upload_reader import read_tabular_upload
from .import_mapping import map_import_rows, suggest_column_mapping


def import_uploaded_dataset(
    store: ProjectStore,
    project_id: str,
    dataset: str,
    uploaded_file: Any,
    *,
    mapping: dict[str, str] | None = None,
    sheet_name: str | None = None,
    mode: str = "upsert",
) -> dict[str, Any]:
    """Parse, map, validate and save one uploaded dataset into a project."""
    project_id = str(project_id).strip()
    if not project_id:
        raise ValueError("project_id is required")
    if dataset not in TABLE_KEYS:
        raise ValueError(f"Unsupported dataset: {dataset}")
    if mode not in {"upsert", "replace"}:
        raise ValueError("mode must be 'upsert' or 'replace'")

    # Streamlit uploads and file-like objects may already have been read for preview.
    # Always parse from byte zero so the service is safe for direct and UI callers.
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    parsed = read_tabular_upload(uploaded_file, sheet_name=sheet_name)
    suggestion = suggest_column_mapping(dataset, parsed["columns"])
    if mapping is None:
        if suggestion["ambiguous"] or suggestion["missing_required"]:
            return {
                "status": "MAPPING_REQUIRED",
                "file": parsed["filename"],
                "dataset": dataset,
                "suggestion": suggestion,
                "saved_count": 0,
            }
        mapping = suggestion["mapping"]

    mapped = map_import_rows(dataset, parsed["rows"], mapping)
    validation = mapped["validation"]
    if validation["status"] != "VALID":
        return {
            "status": "VALIDATION_FAILED",
            "file": parsed["filename"],
            "dataset": dataset,
            "validation": validation,
            "saved_count": 0,
        }

    rows = mapped["rows"]
    mismatched = [
        index for index, row in enumerate(rows)
        if str(row.get("project_id", "")).strip() != project_id
    ]
    if mismatched:
        return {
            "status": "PROJECT_SCOPE_MISMATCH",
            "file": parsed["filename"],
            "dataset": dataset,
            "mismatched_rows": mismatched,
            "saved_count": 0,
        }

    saved = store.save_dataset(project_id, dataset, rows, mode=mode)
    return {
        "status": "COMMITTED",
        "file": parsed["filename"],
        "dataset": dataset,
        "validation": validation,
        "persistence": saved,
        "saved_count": saved["saved_count"],
    }
