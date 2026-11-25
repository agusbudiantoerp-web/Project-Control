"""Streamlit UI for importing and persisting validated project datasets."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .data_quality_validation import TABLE_KEYS
from .import_mapping import suggest_column_mapping
from .project_store import ProjectStore
from .upload_reader import read_tabular_upload
from .import_service import import_uploaded_dataset


def render_persistent_import_ui(database_path: str | Path = ".project_control/project_control.sqlite3") -> dict[str, Any] | None:
    """Render persistent import workflow; replace requires an explicit choice."""
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to render this component.") from exc

    st.subheader("Project Data Import & Storage")
    project_id = st.text_input("Project ID", key="pc_persist_project_id").strip()
    dataset = st.selectbox("Dataset", options=list(TABLE_KEYS), key="pc_persist_dataset")
    uploaded = st.file_uploader("Upload CSV/XLSX", type=["csv", "xlsx"], key="pc_persist_upload")
    if not project_id or uploaded is None:
        st.info("Enter a Project ID and upload a CSV/XLSX file.")
        return None

    try:
        parsed = read_tabular_upload(uploaded)
    except Exception as exc:
        st.error(f"File could not be read: {exc}")
        return {"status": "READ_ERROR", "message": str(exc)}

    st.caption(f"{parsed['filename']} · {parsed['row_count']} rows")
    st.dataframe(parsed["preview"], use_container_width=True)
    suggestion = suggest_column_mapping(dataset, parsed["columns"])
    if suggestion["ambiguous"]:
        st.warning(f"Ambiguous source columns: {suggestion['ambiguous']}")

    targets = list(dict.fromkeys((*TABLE_KEYS[dataset], *suggestion["mapping"].keys())))
    mapping: dict[str, str] = {}
    choices = ["— not mapped —", *parsed["columns"]]
    for target in targets:
        default = suggestion["mapping"].get(target)
        selected = st.selectbox(
            f"Map {target}",
            choices,
            index=choices.index(default) if default in choices else 0,
            key=f"pc_persist_map_{dataset}_{target}",
        )
        if selected != "— not mapped —":
            mapping[target] = selected

    mode_label = st.radio(
        "Import mode",
        ["Upsert (update/add records)", "Replace this dataset"],
        horizontal=True,
        key="pc_persist_mode",
    )
    mode = "replace" if mode_label.startswith("Replace") else "upsert"
    confirm_replace = True
    if mode == "replace":
        st.warning("Replace will remove existing records for this project and dataset before saving the uploaded rows.")
        confirm_replace = st.checkbox(
            "I confirm that I want to replace this project's entire selected dataset.",
            key=f"pc_persist_confirm_replace_{project_id}_{dataset}",
        )

    if not st.button(
        "Validate and save dataset",
        key="pc_persist_submit",
        disabled=not confirm_replace,
    ):
        return {"status": "READY_FOR_REVIEW", "suggestion": suggestion}

    try:
        # The preview parser may consume the upload stream; rewind before import.
        uploaded.seek(0)
        store = ProjectStore(database_path)
        result = import_uploaded_dataset(
            store, project_id, dataset, uploaded,
            mapping=mapping, mode=mode,
        )
    except Exception as exc:
        st.error(f"Import was not committed: {exc}")
        return {"status": "IMPORT_ERROR", "message": str(exc)}

    if result["status"] == "COMMITTED":
        st.success(f"Saved {result['saved_count']} records to project {project_id}.")
        st.json(result["persistence"])
    else:
        st.error(f"Import stopped: {result['status']}")
        if "validation" in result:
            st.dataframe(result["validation"]["issues"], use_container_width=True)
        if "suggestion" in result:
            st.json(result["suggestion"])
    return result
