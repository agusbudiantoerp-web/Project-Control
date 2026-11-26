"""Streamlit entry point for AI Project Control."""
import streamlit as st

from ai_project_control.streamlit_workspace_dashboard import render_project_workspace_dashboard
from ai_project_control.workspace_config import get_workspace_database_path

st.set_page_config(
    page_title="AI Project Control",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stAppViewContainer"] {background: #0b1220;}
    [data-testid="stHeader"] {background: rgba(11,18,32,.88);}
    [data-testid="stSidebar"] {background: #101b2b; border-right: 1px solid #26364a;}
    [data-testid="stMetric"] {background: linear-gradient(145deg,#14243a,#101b2b);
        border: 1px solid #2b4058; padding: 16px 18px; border-radius: 10px;}
    [data-testid="stDataFrame"] {border: 1px solid #26384d; border-radius: 8px;}
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 7px; border: 1px solid #2d9c91; font-weight: 600;
    }
    h1, h2, h3 {letter-spacing: -.02em;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div style="padding:26px 30px; margin:0 0 22px; border:1px solid #29435a;
    border-left:5px solid #36b6a5; border-radius:12px;
    background:linear-gradient(110deg,#14283d 0%,#101b2b 65%,#172437 100%);">
      <div style="font-size:11px; letter-spacing:2.4px; color:#73cfc2; font-weight:700;">
        PROJECT DELIVERY • COST • RISK • PERFORMANCE
      </div>
      <div style="font-size:32px; line-height:1.2; color:#f3f7fb; font-weight:750;
      margin-top:9px;">AI Project Control</div>
      <div style="font-size:14px; color:#b8c8d8; margin-top:9px;">
        Integrated project intelligence for execution control and management decisions.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.info(
    "Local workspace: data tersimpan di SQLite pada komputer ini. Untuk penggunaan "
    "multi-user, siapkan autentikasi, kontrol akses, backup terjadwal, dan database bersama."
)
render_project_workspace_dashboard(get_workspace_database_path())
