"""Streamlit entry point for AI Project Control."""
import streamlit as st

from ai_project_control.streamlit_workspace_dashboard import render_project_workspace_dashboard

st.set_page_config(
    page_title="AI Project Control",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("AI Project Control")
st.caption("Project execution, portfolio governance, risk, forecasting and recovery decision support.")
st.warning(
    "Workspace ini menggunakan SQLite lokal. Sebelum deployment multi-user, "
    "aktifkan autentikasi, kontrol akses, backup, dan penyimpanan database bersama."
)
render_project_workspace_dashboard()
