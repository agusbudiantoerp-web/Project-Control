"""Primary Streamlit entry point for persistent Project Workspace data."""
from __future__ import annotations

import streamlit as st

from ai_project_control.streamlit_persistent_import_ui import render_persistent_import_ui
from ai_project_control.streamlit_workspace_dashboard import render_project_workspace_dashboard
from ai_project_control.workspace_config import get_workspace_database_path

st.set_page_config(page_title="Project Workspace", page_icon="🏗️", layout="wide")
st.title("Project Workspace")
st.caption(
    "Import and validate project datasets, save them in the persistent workspace, "
    "then review project and portfolio controls from the same SQLite database."
)

database_path = get_workspace_database_path()

render_persistent_import_ui(database_path)
project_id = st.session_state.get("pc_persist_project_id", "").strip()
st.divider()
render_project_workspace_dashboard(database_path, project_id=project_id)
