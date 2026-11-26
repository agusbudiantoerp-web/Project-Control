"""Shared Industrial Futuristic visual system for AI Project Control."""
import streamlit as st


def apply_project_control_theme(section: str, subtitle: str, code: str = "PROJECT CONTROLS") -> None:
    """Apply a consistent dark industrial-futuristic UI without changing app logic."""
    st.markdown(
        """
        <style>
        :root {
          color-scheme: dark;
          --pc-bg: #07111f;
          --pc-panel: #101e30;
          --pc-panel-2: #14263a;
          --pc-line: rgba(104, 160, 190, .22);
          --pc-text: #e7f2fa;
          --pc-muted: #91aabd;
          --pc-cyan: #45d9e8;
          --pc-teal: #36d6b0;
          --pc-amber: #ffbf69;
        }
        html, body, [class*="css"] { font-family: Inter, "Segoe UI", sans-serif; }
        .stApp {
          color: var(--pc-text);
          background:
            radial-gradient(ellipse at 8% 0%, rgba(28, 112, 150, .20), transparent 34%),
            radial-gradient(ellipse at 94% 12%, rgba(26, 174, 151, .13), transparent 30%),
            linear-gradient(145deg, #07111f 0%, #0a1727 52%, #081321 100%);
        }
        [data-testid="stAppViewContainer"] { background: transparent; }
        [data-testid="stHeader"] { background: rgba(7,17,31,.72); backdrop-filter: blur(14px); }
        [data-testid="stToolbar"] { right: 1rem; }
        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #0b1929 0%, #0d2032 55%, #0a1726 100%);
          border-right: 1px solid var(--pc-line);
        }
        [data-testid="stSidebar"] * { color: #dcebf5; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #9db6c8; }
        .block-container { padding-top: 1.7rem; padding-bottom: 3.5rem; max-width: 1580px; }
        h1, h2, h3, h4 { color: #f0f8ff; letter-spacing: -.025em; }
        h2, h3 { margin-top: 1.1rem; }
        p, label, .stCaption, [data-testid="stMarkdownContainer"] { color: var(--pc-text); }
        .pc-hero {
          position: relative; overflow: hidden;
          background: linear-gradient(112deg, rgba(16,38,58,.98), rgba(12,48,65,.96) 58%, rgba(10,77,77,.92));
          border: 1px solid rgba(69,217,232,.34); border-left: 4px solid var(--pc-cyan);
          padding: 1.65rem 1.9rem; border-radius: 18px; margin: .2rem 0 1.35rem;
          box-shadow: 0 14px 42px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.05);
        }
        .pc-hero:after {
          content: ""; position: absolute; width: 240px; height: 240px; right: -70px; top: -130px;
          border: 1px solid rgba(69,217,232,.22); border-radius: 50%;
          box-shadow: 0 0 0 22px rgba(69,217,232,.035), 0 0 0 48px rgba(69,217,232,.025);
          pointer-events: none;
        }
        .pc-kicker { color: var(--pc-cyan); font-size: .70rem; letter-spacing: .19em; font-weight: 800; }
        .pc-title { color: #f5fbff; font-size: clamp(1.55rem, 3vw, 2.15rem); line-height: 1.15; font-weight: 800; margin: .48rem 0 .4rem; }
        .pc-subtitle { color: #b6cbd9; font-size: .94rem; margin: 0; max-width: 850px; }
        [data-testid="stMetric"] {
          background: linear-gradient(145deg, rgba(20,42,62,.96), rgba(12,27,43,.96));
          border: 1px solid var(--pc-line); border-radius: 14px; padding: 15px 17px;
          box-shadow: 0 8px 24px rgba(0,0,0,.15), inset 0 1px 0 rgba(255,255,255,.035);
        }
        [data-testid="stMetricLabel"] { color: #9db7c9 !important; font-weight: 650; }
        [data-testid="stMetricValue"] { color: #f0fbff !important; font-weight: 800; }
        [data-testid="stMetricDelta"] { font-weight: 650; }
        div[data-testid="stForm"], div[data-testid="stExpander"] {
          background: rgba(13,29,46,.82); border: 1px solid var(--pc-line);
          border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,.10);
        }
        [data-testid="stExpander"] summary { color: #e8f5fc; font-weight: 700; }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
          border: 1px solid var(--pc-line); border-radius: 12px; overflow: hidden;
        }
        [data-baseweb="input"] > div, [data-baseweb="select"] > div,
        [data-baseweb="textarea"], [data-testid="stDateInput"] input,
        [data-testid="stNumberInput"] input {
          background: #0b1a2b !important; border-color: #29465e !important; color: #eaf6fc !important;
          border-radius: 9px !important;
        }
        input, textarea { color: #eaf6fc !important; }
        [data-testid="stFileUploader"] {
          background: rgba(15,36,55,.72); border: 1px dashed rgba(69,217,232,.42);
          border-radius: 13px; padding: .55rem;
        }
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
          border-radius: 10px; min-height: 2.55rem; font-weight: 750;
          border: 1px solid rgba(69,217,232,.48);
          background: linear-gradient(105deg, #087e89, #087b70); color: #f4ffff;
          box-shadow: 0 5px 16px rgba(0,174,180,.13); transition: all .18s ease;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
          border-color: var(--pc-cyan); background: linear-gradient(105deg, #0996a2, #07917f);
          color: white; transform: translateY(-1px); box-shadow: 0 8px 22px rgba(0,210,210,.2);
        }
        button[kind="secondary"] { background: #132a40 !important; border-color: #31536c !important; }
        [data-testid="stAlert"] { border-radius: 12px; border: 1px solid var(--pc-line); }
        [data-testid="stTabs"] button { color: #a9c0d0; font-weight: 700; }
        [data-testid="stTabs"] button[aria-selected="true"] { color: var(--pc-cyan); }
        [data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #20a9bb, #39d6ad); }
        hr { border-color: var(--pc-line); }
        code { color: #72e4e7; background: #10263a; border-radius: 5px; }
        a { color: var(--pc-cyan) !important; }
        @media (max-width: 760px) {
          .block-container { padding-left: 1rem; padding-right: 1rem; }
          .pc-hero { padding: 1.25rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="pc-hero"><div class="pc-kicker">{code}</div>'
        f'<div class="pc-title">{section}</div>'
        f'<p class="pc-subtitle">{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
