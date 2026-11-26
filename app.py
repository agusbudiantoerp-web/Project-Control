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
    with st.container(border=True):
        st.page_link("pages/01_Project_Workspace.py", label="PROJECT WORKSPACE", icon="🏗️", use_container_width=True)
        st.caption("Project records, imports and validation")
with nav[1]:
    with st.container(border=True):
        st.page_link("pages/02_Dated_Cash_Flow.py", label="CASH FLOW", icon="💧", use_container_width=True)
        st.caption("Dated actual and forecast liquidity")
with nav[2]:
    with st.container(border=True):
        st.page_link("pages/03_EVM_Cost_Control.py", label="EVM & COST CONTROL", icon="📈", use_container_width=True)
        st.caption("PV, EV, AC, SPI, CPI and EAC")
with nav[3]:
    with st.container(border=True):
        st.page_link("pages/06_Saved_Portfolio_COO_Cockpit.py", label="COO COCKPIT", icon="🛰️", use_container_width=True)
        st.caption("Portfolio exposure and executive priorities")
st.markdown(
    '<div class="pc-status-strip"><span><i></i> LOCAL WORKSPACE</span>'
    '<span>DATA GOVERNANCE ENABLED</span><span>PROJECT CONTROL / 01</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="pc-section-label">INTELLIGENCE & GOVERNANCE / SYSTEM MODULES</div>',
    unsafe_allow_html=True,
)
more = st.columns(5, gap="medium")
with more[0]:
    with st.container(border=True):
        st.page_link("pages/04_Telegram_Executive_Report.py", label="TELEGRAM REPORT", icon="📡", use_container_width=True)
        st.caption("Review and authorize executive updates")
with more[1]:
    with st.container(border=True):
        st.page_link("pages/05_Saved_Project_Financial_Control.py", label="PROJECT FINANCE", icon="💹", use_container_width=True)
        st.caption("Saved project financial assessments")
with more[2]:
    with st.container(border=True):
        st.page_link("pages/07_Workspace_Backup_Audit.py", label="BACKUP & AUDIT", icon="🛡️", use_container_width=True)
        st.caption("Data lineage and recovery snapshots")
with more[3]:
    with st.container(border=True):
        st.page_link("pages/08_Primavera_XER_Drawing_BOQ_Intake.py", label="P6 / BOQ INTAKE", icon="📐", use_container_width=True)
        st.caption("Schedule and engineering quantity intake")
with more[4]:
    with st.container(border=True):
        st.page_link("pages/09_AI_Project_Advisor.py", label="AI ADVISOR", icon="🤖", use_container_width=True)
        st.caption("Evidence-based management insights")
st.markdown(
    '<div class="pc-section-label">PORTFOLIO OPERATIONS / LIVE WORKSPACE</div>',
    unsafe_allow_html=True,
)
render_project_workspace_dashboard(get_workspace_database_path(), show_project_selector=False)
