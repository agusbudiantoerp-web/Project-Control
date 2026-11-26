"""Streamlit entry point for AI Project Control."""
import streamlit as st

from ai_project_control.streamlit_workspace_dashboard import render_project_workspace_dashboard
from ai_project_control.workspace_config import get_workspace_database_path
from ai_project_control.ui_theme import apply_project_control_theme

st.set_page_config(
    page_title="AI Project Control",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_project_control_theme(
    "AI Project Control",
    "Integrated project intelligence for execution control and management decisions.",
    "PROJECT DELIVERY • COST • RISK • PERFORMANCE",
)
st.info(
    "Local workspace: data tersimpan di SQLite pada komputer ini. Untuk penggunaan "
    "multi-user, siapkan autentikasi, kontrol akses, backup terjadwal, dan database bersama."
)
render_project_workspace_dashboard(get_workspace_database_path())
