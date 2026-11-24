"""Primary Streamlit entry point for persistent Project Workspace data."""
from __future__ import annotations

import os
import streamlit as st

from ai_project_control.streamlit_persistent_import_ui import render_persistent_import_ui
from ai_project_control.streamlit_workspace_dashboard import render_project_workspace_dashboard

st.set_page_config(page_title="Project Workspace", page_icon="🏗️", layout="wide")
st.title("Project Workspace")
st.caption(
    "Import and validate project datasets, save them in the persistent workspace, "
    "then review project and portfolio controls from the same SQLite database."
)

database_path = os.getenv("PROJECT_CONTROL_DB", ".project_control/project_control.sqlite3")

render_persistent_import_ui(database_path)
st.divider()
render_project_workspace_dashboard(database_path)
