"""Premium futuristic industrial UI system shared by all AI Project Control pages."""
import streamlit as st


def apply_project_control_theme(section: str, subtitle: str, code: str = "PROJECT CONTROLS") -> None:
    """Render a high-contrast command-center shell without touching business logic."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');
        :root {
          color-scheme: dark;
          --pc-bg:#050b14; --pc-panel:#0b1725; --pc-panel2:#102337;
          --pc-line:rgba(83,190,211,.24); --pc-cyan:#55e6f2;
          --pc-teal:#35e0b3; --pc-amber:#ffbd66; --pc-text:#eaf7ff;
          --pc-muted:#91aabd;
        }
        html,body,[class*="css"] {font-family:Inter,"Segoe UI",sans-serif;}
        .stApp {
          color:var(--pc-text);
          background:
            radial-gradient(ellipse at 12% 4%,rgba(0,192,220,.17),transparent 27%),
            radial-gradient(ellipse at 90% 14%,rgba(0,220,166,.11),transparent 26%),
            linear-gradient(135deg,#040a12 0%,#081522 48%,#07101b 100%);
          background-attachment:fixed;
        }
        [data-testid="stAppViewContainer"]{background:transparent;}
        [data-testid="stHeader"]{background:rgba(4,10,18,.76);backdrop-filter:blur(18px);border-bottom:1px solid rgba(88,200,220,.12);}
        [data-testid="stToolbar"]{right:1rem;}
        .block-container{max-width:1660px;padding-top:1.25rem;padding-bottom:4rem;}
        [data-testid="stSidebar"]{
          background:linear-gradient(180deg,#071321 0%,#0a1b2b 48%,#06111d 100%);
          border-right:1px solid rgba(85,230,242,.22);
          box-shadow:8px 0 36px rgba(0,0,0,.22);
        }
        [data-testid="stSidebar"] *{color:#dcecf7;}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#9bb7c9;}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{
          border:1px solid transparent;border-radius:9px;margin:3px 0;transition:all .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{
          background:rgba(40,191,207,.12);border-color:rgba(85,230,242,.25);
        }
        .pc-brand{display:flex;align-items:center;gap:11px;padding:13px 12px;margin:2px 0 22px;
          border:1px solid rgba(85,230,242,.26);border-radius:13px;
          background:linear-gradient(115deg,rgba(15,47,67,.96),rgba(8,27,43,.82));
          box-shadow:0 8px 28px rgba(0,0,0,.22);}
        .pc-brand-mark{width:38px;height:38px;display:grid;place-items:center;border-radius:10px;
          color:#03131b;background:linear-gradient(140deg,#61f1fa,#24c9a7);font-weight:900;font-size:20px;
          box-shadow:0 0 20px rgba(57,220,221,.28);}
        .pc-brand-name{font-size:12px;letter-spacing:.14em;font-weight:900;color:#f1fcff;}
        .pc-brand-sub{font-family:"DM Mono",monospace;font-size:9px;letter-spacing:.12em;color:#7fa8bd;margin-top:3px;}
        h1,h2,h3,h4{color:#f0faff;letter-spacing:-.025em;}
        h2{font-weight:800;margin-top:1.4rem;}
        h3{font-weight:750;}
        p,label,.stCaption,[data-testid="stMarkdownContainer"]{color:var(--pc-text);}
        .pc-topline{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 0 10px;
          color:#7fa8bd;font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.15em;text-transform:uppercase;}
        .pc-live{display:inline-flex;align-items:center;gap:7px;color:#68edc4;}
        .pc-live:before{content:"";width:7px;height:7px;border-radius:50%;background:#35e0b3;box-shadow:0 0 12px #35e0b3;}
        .pc-hero{
          position:relative;isolation:isolate;overflow:hidden;min-height:190px;
          padding:28px 32px 26px;margin:0 0 22px;border-radius:18px;
          border:1px solid rgba(85,230,242,.38);border-left:4px solid #55e6f2;
          background:
            linear-gradient(100deg,rgba(7,25,41,.98) 0%,rgba(9,45,61,.96) 55%,rgba(5,75,72,.88) 100%);
          box-shadow:0 18px 48px rgba(0,0,0,.34),inset 0 1px rgba(255,255,255,.06);
        }
        .pc-hero:before{content:"";position:absolute;inset:0;z-index:-1;opacity:.24;
          background-image:linear-gradient(rgba(87,210,225,.18) 1px,transparent 1px),
          linear-gradient(90deg,rgba(87,210,225,.18) 1px,transparent 1px);
          background-size:34px 34px;mask-image:linear-gradient(90deg,black,transparent 78%);}
        .pc-hero:after{content:"";position:absolute;z-index:-1;width:280px;height:280px;right:5%;top:-145px;
          border:1px solid rgba(85,230,242,.32);border-radius:50%;
          box-shadow:0 0 0 24px rgba(85,230,242,.035),0 0 0 52px rgba(85,230,242,.025),0 0 65px rgba(40,220,210,.10);}
        .pc-hero-grid{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;}
        .pc-kicker{font-family:"DM Mono",monospace;color:#62eaf2;font-size:10px;letter-spacing:.22em;font-weight:500;}
        .pc-title{font-family:"Barlow Condensed",Inter,sans-serif;color:#f6fdff;font-size:clamp(38px,5vw,58px);
          line-height:.98;font-weight:800;letter-spacing:.015em;text-transform:uppercase;margin:12px 0 10px;
          text-shadow:0 0 24px rgba(85,230,242,.12);}
        .pc-subtitle{color:#b5cfdd;font-size:13px;line-height:1.65;margin:0;max-width:780px;}
        .pc-hero-side{min-width:150px;text-align:right;border-left:1px solid rgba(85,230,242,.22);padding-left:22px;}
        .pc-hero-side strong{display:block;color:#6df2d1;font-family:"Barlow Condensed",sans-serif;font-size:28px;letter-spacing:.08em;}
        .pc-hero-side span{display:block;color:#8eafc1;font-family:"DM Mono",monospace;font-size:9px;letter-spacing:.13em;}
        .pc-section-label{display:flex;align-items:center;gap:10px;margin:25px 0 12px;color:#75dfe8;
          font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;}
        .pc-section-label:after{content:"";height:1px;flex:1;background:linear-gradient(90deg,rgba(85,230,242,.35),transparent);}
        [data-testid="stMetric"]{
          position:relative;overflow:hidden;min-height:112px;padding:17px 18px;
          border-radius:13px;border:1px solid rgba(85,190,211,.25);
          background:linear-gradient(145deg,rgba(17,42,62,.98),rgba(7,20,34,.98));
          box-shadow:0 10px 26px rgba(0,0,0,.23),inset 0 1px rgba(255,255,255,.045);
        }
        [data-testid="stMetric"]:before{content:"";position:absolute;top:0;left:0;width:48px;height:2px;
          background:linear-gradient(90deg,#55e6f2,transparent);box-shadow:0 0 12px #55e6f2;}
        [data-testid="stMetricLabel"]{color:#91b2c4!important;font-family:"DM Mono",monospace;font-size:10px!important;letter-spacing:.08em;text-transform:uppercase;}
        [data-testid="stMetricValue"]{color:#f2fcff!important;font-family:"Barlow Condensed",sans-serif;font-size:32px!important;font-weight:700;}
        [data-testid="stMetricDelta"]{font-family:"DM Mono",monospace;font-size:11px;}
        div[data-testid="stForm"],div[data-testid="stExpander"]{
          background:linear-gradient(145deg,rgba(12,30,47,.94),rgba(8,20,33,.94));
          border:1px solid rgba(82,174,198,.22);border-radius:13px;
          box-shadow:0 10px 28px rgba(0,0,0,.16);
        }
        [data-testid="stExpander"] summary{color:#e8f8ff;font-weight:700;}
        [data-testid="stDataFrame"],[data-testid="stDataEditor"]{border:1px solid rgba(85,190,211,.25);border-radius:11px;overflow:hidden;}
        [data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"],
        [data-testid="stDateInput"] input,[data-testid="stNumberInput"] input{
          background:#081827!important;border-color:#29495e!important;color:#effaff!important;border-radius:8px!important;
        }
        input,textarea{color:#effaff!important;}
        [data-testid="stFileUploader"]{background:rgba(9,29,46,.78);border:1px dashed rgba(85,230,242,.46);border-radius:13px;padding:10px;}
        .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{
          min-height:43px;border-radius:9px;border:1px solid rgba(85,230,242,.56);
          background:linear-gradient(110deg,#087e91,#087d70);color:#f5ffff;font-weight:800;
          letter-spacing:.025em;box-shadow:0 6px 20px rgba(0,190,195,.15);transition:all .18s ease;
        }
        .stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{
          transform:translateY(-2px);border-color:#7af4fa;background:linear-gradient(110deg,#0a9fb2,#099780);
          box-shadow:0 10px 26px rgba(0,220,215,.25);color:white;
        }
        button[kind="secondary"]{background:linear-gradient(110deg,#132b40,#102638)!important;border-color:#31556d!important;}
        [data-testid="stAlert"]{border-radius:11px;border:1px solid rgba(85,190,211,.24);background:rgba(12,31,47,.86);}
        [data-testid="stTabs"] button{color:#9bb8c8;font-weight:750;}
        [data-testid="stTabs"] button[aria-selected="true"]{color:#62eaf2;border-bottom-color:#62eaf2;}
        [data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,#20a9bb,#35e0b3);}
        [data-testid="stPlotlyChart"],[data-testid="stVegaLiteChart"],[data-testid="stArrowVegaLiteChart"]{
          border:1px solid rgba(85,190,211,.18);border-radius:13px;background:rgba(9,25,40,.55);padding:5px;
        }
        hr{border-color:rgba(85,190,211,.2);}
        code{color:#72eaf0;background:#10283b;border-radius:5px;}
        a{color:#62eaf2!important;}
        @media(max-width:850px){.pc-hero-grid{grid-template-columns:1fr}.pc-hero-side{display:none}.pc-hero{padding:23px 20px}.pc-title{font-size:39px}}
        @media(max-width:760px){.block-container{padding-left:1rem;padding-right:1rem}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="pc-brand"><div class="pc-brand-mark">⌁</div>'
        '<div><div class="pc-brand-name">AI PROJECT CONTROL</div>'
        '<div class="pc-brand-sub">INDUSTRIAL INTELLIGENCE SYSTEM</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pc-topline"><span>PROJECT INTELLIGENCE / COMMAND INTERFACE</span>'
        '<span class="pc-live">SYSTEM WORKSPACE</span></div>'
        f'<div class="pc-hero"><div class="pc-hero-grid"><div>'
        f'<div class="pc-kicker">{code}</div><div class="pc-title">{section}</div>'
        f'<p class="pc-subtitle">{subtitle}</p></div>'
        '<div class="pc-hero-side"><strong>CONTROL<br>HUB</strong><span>LIVE OPERATIONS VIEW</span></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
