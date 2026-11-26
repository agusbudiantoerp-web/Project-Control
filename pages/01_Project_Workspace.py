"""Primary Streamlit entry point for persistent Project Workspace data."""
from __future__ import annotations

import streamlit as st

from ai_project_control.streamlit_persistent_import_ui import render_persistent_import_ui
from ai_project_control.streamlit_workspace_dashboard import render_project_workspace_dashboard
from ai_project_control.workspace_config import get_workspace_database_path\nfrom ai_project_control.ui_theme import apply_project_control_theme

st.set_page_config(page_title="Project Workspace", page_icon="🏗️", layout="wide")
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stMetric"] {background: linear-gradient(145deg,#14243a,#101b2b);
        border: 1px solid #2b4058; padding: 14px 16px; border-radius: 10px;}
    [data-testid="stDataFrame"] {border: 1px solid #26384d; border-radius: 8px;}
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 7px; border: 1px solid #2d9c91; font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div style="padding:22px 26px; margin:0 0 20px; border:1px solid #29435a;
    border-left:5px solid #36b6a5; border-radius:11px;
    background:linear-gradient(110deg,#14283d 0%,#101b2b 70%,#172437 100%);">
      <div style="font-size:10px; letter-spacing:2px; color:#73cfc2; font-weight:700;">
        DATA INTAKE • VALIDATION • PROJECT GOVERNANCE
      </div>
      <div style="font-size:28px; color:#f3f7fb; font-weight:750; margin-top:8px;">
        Project Workspace
      </div>
      <div style="font-size:13px; color:#b8c8d8; margin-top:7px;">
        Import, validate and maintain project information in one controlled workspace.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Import and validate project datasets, save them in the persistent workspace, "
    "then review project and portfolio controls from the same SQLite database."
)

database_path = get_workspace_database_path()

render_persistent_import_ui(database_path)
project_id = st.session_state.get("pc_persist_project_id", "").strip()
st.divider()
render_project_workspace_dashboard(database_path, project_id=project_id)
