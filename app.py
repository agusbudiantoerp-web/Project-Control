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
st.markdown(
    '<div class="pc-notice"><strong>LOCAL DATA MODE</strong> &nbsp; Data workspace tersimpan '
    'di SQLite pada komputer ini. Untuk penggunaan multi-user, siapkan autentikasi, '
    'kontrol akses, backup terjadwal, dan database bersama.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="pc-section-label">QUICK ACCESS / OPERATIONS MODULES</div>',
    unsafe_allow_html=True,
)
nav = st.columns(4, gap="medium")
with nav[0]:
    st.page_link("pages/01_Project_Workspace.py", label="PROJECT WORKSPACE", icon="🏗️", use_container_width=True)
with nav[1]:
    st.page_link("pages/02_Dated_Cash_Flow.py", label="CASH FLOW", icon="💧", use_container_width=True)
with nav[2]:
    st.page_link("pages/03_EVM_Cost_Control.py", label="EVM & COST CONTROL", icon="📈", use_container_width=True)
with nav[3]:
    st.page_link("pages/06_Saved_Portfolio_COO_Cockpit.py", label="COO COCKPIT", icon="🛰️", use_container_width=True)
st.markdown(
    '<div class="pc-status-strip"><span><i></i> LOCAL WORKSPACE</span>'
    '<span>DATA GOVERNANCE ENABLED</span><span>PROJECT CONTROL / 01</span></div>',
    unsafe_allow_html=True,
)
render_project_workspace_dashboard(get_workspace_database_path())
