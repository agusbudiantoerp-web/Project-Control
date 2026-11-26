"""Shared visual system for the AI Project Control Streamlit workspace."""
import streamlit as st


def apply_project_control_theme(section: str, subtitle: str, code: str = "PROJECT CONTROLS") -> None:
    """Apply a restrained industrial dashboard style without changing business logic."""
    st.markdown(
        """
        <style>
        .stApp { background:#f3f6f8; color:#172536; }
        [data-testid="stHeader"] { background:rgba(243,246,248,.92); }
        [data-testid="stSidebar"] { background:#142536; }
        [data-testid="stSidebar"] * { color:#e8eef3 !important; }
        .block-container { padding-top:1.7rem; padding-bottom:3rem; max-width:1500px; }
        .pc-hero { background:linear-gradient(115deg,#142536 0%,#203d50 72%,#176b70 100%);
          padding:1.55rem 1.8rem; border-radius:16px; margin:.25rem 0 1.2rem;
          box-shadow:0 8px 24px rgba(20,37,54,.12); }
        .pc-kicker { color:#8ed7cf; font-size:.72rem; letter-spacing:.16em; font-weight:750; }
        .pc-title { color:#fff; font-size:1.8rem; line-height:1.2; font-weight:750; margin:.45rem 0 .35rem; }
        .pc-subtitle { color:#d2dfe7; font-size:.94rem; margin:0; }
        div[data-testid="stMetric"] { background:#fff; border:1px solid #e0e7ec;
          border-radius:12px; padding:14px 16px; box-shadow:0 3px 12px rgba(20,37,54,.04); }
        div[data-testid="stMetricLabel"] { color:#637587; font-weight:650; }
        div[data-testid="stMetricValue"] { color:#142536; }
        div[data-testid="stForm"] { background:#fff; border:1px solid #e0e7ec; border-radius:14px; padding:1rem 1.1rem; }
        div[data-testid="stExpander"] { background:#fff; border:1px solid #e0e7ec; border-radius:12px; }
        .stButton > button, .stFormSubmitButton > button { border-radius:9px; font-weight:650;
          border:0; background:#176b70; color:#fff; min-height:2.55rem; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#12575b; color:#fff; }
        div[data-testid="stDataFrame"] { border:1px solid #e0e7ec; border-radius:10px; overflow:hidden; }
        hr { border-color:#dce5ea; }
        </style>
        """, unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="pc-hero"><div class="pc-kicker">{code}</div>'
        f'<div class="pc-title">{section}</div>'
        f'<p class="pc-subtitle">{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
