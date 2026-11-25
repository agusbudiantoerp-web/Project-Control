"""Reusable Streamlit upload-preview component (no persistence side effects).

Call render_upload_import_ui() from the confirmed application entry point when
one is available. The component deliberately stops after preview and validation.
"""
from __future__ import annotations

from typing import Any

from .data_quality_validation import TABLE_KEYS
from .import_mapping import map_import_rows, suggest_column_mapping
from .upload_reader import read_tabular_upload


def render_upload_import_ui() -> dict[str, Any] | None:
    """Render an upload, mapping review and validation preview in Streamlit."""
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to render this component.") from exc

    st.subheader("Project Data Import")
    st.caption("Upload CSV/XLSX, review column mapping, then validate. No records are saved.")
    table = st.selectbox("Dataset", options=list(TABLE_KEYS), key="pc_import_table")
    uploaded = st.file_uploader(
        "Choose CSV or XLSX",
        type=["csv", "xlsx"],
        key="pc_import_file",
    )
    if uploaded is None:
        st.info("Upload a file to begin the import preview.")
        return None

    try:
        parsed = read_tabular_upload(uploaded)
    except Exception as exc:
        st.error(f"Unable to read upload: {exc}")
        return {"status": "READ_ERROR", "message": str(exc)}

    st.write(f"File: {parsed['filename']} · {parsed['row_count']} rows")
    st.dataframe(parsed["preview"], use_container_width=True)

    suggestion = suggest_column_mapping(table, parsed["columns"])
    st.write("Suggested column mapping")
    mapping: dict[str, str] = {}
    target_fields = list(dict.fromkeys((*TABLE_KEYS[table], *suggestion["mapping"].keys())))
    for target in target_fields:
        current = suggestion["mapping"].get(target)
        choices = ["— not mapped —", *parsed["columns"]]
        default_index = choices.index(current) if current in choices else 0
        selected = st.selectbox(
            target,
            options=choices,
            index=default_index,
            key=f"pc_map_{table}_{target}",
        )
        if selected != "— not mapped —":
            mapping[target] = selected

    if not st.button("Validate import preview", key="pc_validate_import"):
        return {"status": "MAPPING_REVIEW", "suggestion": suggestion}

    try:
        result = map_import_rows(table, parsed["rows"], mapping)
    except Exception as exc:
        st.error(f"Mapping failed: {exc}")
        return {"status": "MAPPING_ERROR", "message": str(exc)}

    validation = result["validation"]
    if validation["status"] == "VALID":
        st.success("Validation passed. Preview is ready; no data has been saved.")
    else:
        st.error(f"Validation status: {validation['status']}")
    st.metric("Rows", result["row_count"])
    st.metric("Errors", validation["error_count"])
    st.metric("Warnings", validation["warning_count"])
    if validation["issues"]:
        st.dataframe(validation["issues"], use_container_width=True)
    st.dataframe(result["rows"][:100], use_container_width=True)
    return result
