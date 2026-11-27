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
          --pc-bg:#10091f; --pc-panel:#1a1030; --pc-panel2:#261641;
          --pc-line:rgba(190,145,255,.25); --pc-cyan:#c9a7ff;
          --pc-teal:#f0a6ff; --pc-amber:#ffd58a; --pc-text:#f7f0ff;
          --pc-muted:#b9a8cf;
        }
        html,body,[class*="css"] {font-family:Inter,"Segoe UI",sans-serif;}
        .stApp {
          color:var(--pc-text);
          background:
            radial-gradient(ellipse at 12% 5%,rgba(174,92,255,.27),transparent 30%),
            radial-gradient(ellipse at 88% 13%,rgba(255,92,214,.16),transparent 28%),
            radial-gradient(ellipse at 52% 82%,rgba(88,67,180,.16),transparent 36%),
            radial-gradient(circle at 20% 35%,rgba(255,255,255,.10) 0 1px,transparent 1.8px),
            radial-gradient(circle at 74% 62%,rgba(224,203,255,.12) 0 1px,transparent 2px),
            linear-gradient(135deg,#090512 0%,#160d29 42%,#211238 72%,#0d081b 100%);
          background-attachment:fixed;
        }
        [data-testid="stAppViewContainer"]{background:transparent;}
        [data-testid="stHeader"]{background:rgba(13,7,27,.82);backdrop-filter:blur(18px);border-bottom:1px solid rgba(190,145,255,.18);}
        [data-testid="stToolbar"]{right:1rem;}
        .block-container{max-width:1660px;padding-top:1.25rem;padding-bottom:4rem;}
        [data-testid="stSidebar"]{
          background:linear-gradient(180deg,#10091f 0%,#1b1030 48%,#0c0719 100%);
          border-right:1px solid rgba(192,151,255,.30);
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
        a[data-testid="stPageLink-NavLink"]{
          display:flex;align-items:center;justify-content:center;min-height:68px;
          padding:13px 14px;border:1px solid rgba(85,230,242,.30);border-radius:12px;
          background:linear-gradient(135deg,rgba(65,39,94,.96),rgba(26,15,48,.99));
          box-shadow:0 8px 22px rgba(0,0,0,.2),inset 0 1px rgba(255,255,255,.05);
          transition:all .2s ease;text-decoration:none!important;
        }
        a[data-testid="stPageLink-NavLink"]:hover{
          border-color:#65eff4;background:linear-gradient(135deg,rgba(117,65,166,.95),rgba(91,39,126,.98));
          transform:translateY(-3px);box-shadow:0 12px 28px rgba(0,205,210,.18);
        }
        a[data-testid="stPageLink-NavLink"] p{font-family:"DM Mono",monospace;font-size:10px;
          font-weight:700;letter-spacing:.07em;color:#e8fcff!important;}
        .pc-status-strip{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
          padding:10px 14px;margin:0 0 23px;border:1px solid rgba(85,190,211,.17);
          border-radius:9px;background:rgba(28,17,48,.76);color:#c0afd5;
          font-family:"DM Mono",monospace;font-size:9px;letter-spacing:.12em;}
        .pc-status-strip span:first-child{color:#68edc4;}
        .pc-status-strip i{display:inline-block;width:6px;height:6px;border-radius:50%;
          background:#35e0b3;box-shadow:0 0 10px #35e0b3;margin-right:6px;}
        .pc-notice{padding:12px 15px;margin:0 0 17px;border-left:3px solid #ffbd66;
          border-top:1px solid rgba(255,189,102,.2);border-right:1px solid rgba(255,189,102,.2);
          border-bottom:1px solid rgba(255,189,102,.2);border-radius:8px;
          background:linear-gradient(90deg,rgba(74,51,24,.42),rgba(15,28,39,.7));
          color:#f3d8ad;font-size:12px;line-height:1.6;}
        [data-testid="stSubheader"]{
          position:relative;margin:27px 0 13px;padding:12px 15px 11px 18px;
          border:1px solid rgba(85,190,211,.20);border-left:3px solid #55e6f2;
          border-radius:8px;background:linear-gradient(90deg,rgba(54,31,83,.92),rgba(20,12,37,.48));
          box-shadow:inset 0 1px rgba(255,255,255,.025);
        }
        [data-testid="stSubheader"] h2{
          font-family:"Barlow Condensed",sans-serif;font-size:25px!important;
          letter-spacing:.055em;text-transform:uppercase;color:#e9fbff;
        }
        [data-testid="stSubheader"] p{margin:0;}
        [data-testid="stVerticalBlockBorderWrapper"]{
          border-color:rgba(85,190,211,.2)!important;border-radius:12px!important;
        }
        [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"]{
          min-height:116px;padding:9px 10px;
          background:linear-gradient(145deg,rgba(51,31,76,.97),rgba(19,12,36,.99));
          border:1px solid rgba(85,190,211,.28)!important;
          box-shadow:0 9px 24px rgba(0,0,0,.2),inset 0 1px rgba(255,255,255,.035);
          transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;
        }
        [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"]:hover{
          transform:translateY(-3px);border-color:rgba(85,230,242,.58)!important;
          box-shadow:0 14px 30px rgba(0,0,0,.28),0 0 18px rgba(42,210,220,.09);
        }
        [data-testid="column"] [data-testid="stCaptionContainer"] p{
          min-height:32px;margin:8px 3px 2px;color:#9ab9c9;font-size:10px;
          line-height:1.45;letter-spacing:.015em;
        }
        [data-testid="column"] a[data-testid="stPageLink-NavLink"]{
          min-height:52px;padding:9px 8px;border-radius:8px;
          background:linear-gradient(110deg,rgba(12,83,99,.9),rgba(8,54,60,.9));
          border:1px solid rgba(85,230,242,.24);
        }
        [data-testid="column"] a[data-testid="stPageLink-NavLink"] p{
          font-size:9px;letter-spacing:.035em;white-space:normal;text-align:center;
        }
        [data-testid="column"] a[data-testid="stPageLink-NavLink"] svg{
          filter:drop-shadow(0 0 5px rgba(85,230,242,.45));
        }
        [data-testid="stMetric"]{
          transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;
        }
        [data-testid="stMetric"]:hover{
          transform:translateY(-2px);border-color:rgba(85,230,242,.52);
          box-shadow:0 13px 30px rgba(0,0,0,.28),0 0 18px rgba(40,210,220,.07);
        }
        [data-testid="stPageLink-NavLink"] svg{color:#65eaf1!important;}
        [data-testid="stDataFrame"]{box-shadow:0 8px 22px rgba(0,0,0,.14);}
        [data-testid="stTabs"] [role="tablist"]{
          gap:7px;border-bottom:1px solid rgba(85,190,211,.18);
        }
        [data-testid="stTabs"] button[role="tab"]{
          border:1px solid transparent;border-radius:8px 8px 0 0;padding:9px 14px;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
          background:rgba(20,80,93,.24);border-color:rgba(85,230,242,.25);
        }
        [data-testid="stCaptionContainer"] p{color:#8eacbf;font-size:11px;line-height:1.6;}
        @media(max-width:1000px){
          [data-testid="stPageLink-NavLink"]{min-height:60px;}
        }
        [data-testid="stSubheader"] h2{font-family:"Barlow Condensed",sans-serif;font-size:26px;
          letter-spacing:.045em;text-transform:uppercase;}
        .pc-brand{display:flex;align-items:center;gap:11px;padding:13px 12px;margin:2px 0 22px;
          border:1px solid rgba(85,230,242,.26);border-radius:13px;
          background:linear-gradient(115deg,rgba(66,39,96,.98),rgba(25,15,47,.90));
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
          background:linear-gradient(145deg,rgba(57,36,84,.98),rgba(21,13,39,.99));
          box-shadow:0 10px 26px rgba(0,0,0,.23),inset 0 1px rgba(255,255,255,.045);
        }
        [data-testid="stMetric"]:before{content:"";position:absolute;top:0;left:0;width:48px;height:2px;
          background:linear-gradient(90deg,#55e6f2,transparent);box-shadow:0 0 12px #55e6f2;}
        [data-testid="stMetricLabel"]{color:#91b2c4!important;font-family:"DM Mono",monospace;font-size:10px!important;letter-spacing:.08em;text-transform:uppercase;}
        [data-testid="stMetricValue"]{color:#f2fcff!important;font-family:"Barlow Condensed",sans-serif;font-size:32px!important;font-weight:700;}
        [data-testid="stMetricDelta"]{font-family:"DM Mono",monospace;font-size:11px;}
        div[data-testid="stForm"],div[data-testid="stExpander"]{
          background:linear-gradient(145deg,rgba(42,26,64,.96),rgba(19,12,37,.97));
          border:1px solid rgba(82,174,198,.22);border-radius:13px;
          box-shadow:0 10px 28px rgba(0,0,0,.16);
        }
        [data-testid="stExpander"] summary{color:#e8f8ff;font-weight:700;}
        [data-testid="stDataFrame"],[data-testid="stDataEditor"]{border:1px solid rgba(85,190,211,.25);border-radius:11px;overflow:hidden;}
        [data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"],
        [data-testid="stDateInput"] input,[data-testid="stNumberInput"] input{
          background:#170e29!important;border-color:#634887!important;color:#fbf5ff!important;border-radius:8px!important;
        }
        input,textarea{color:#effaff!important;}
        [data-testid="stFileUploader"]{background:rgba(35,21,56,.82);border:1px dashed rgba(202,166,255,.56);border-radius:13px;padding:10px;}
        .stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{
          min-height:43px;border-radius:9px;border:1px solid rgba(85,230,242,.56);
          background:linear-gradient(110deg,#7442a6,#a34c9f);color:#f5ffff;font-weight:800;
          letter-spacing:.025em;box-shadow:0 6px 20px rgba(0,190,195,.15);transition:all .18s ease;
        }
        .stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{
          transform:translateY(-2px);border-color:#7af4fa;background:linear-gradient(110deg,#9456d0,#c05aaf);
          box-shadow:0 10px 26px rgba(0,220,215,.25);color:white;
        }
        button[kind="secondary"]{background:linear-gradient(110deg,#132b40,#102638)!important;border-color:#31556d!important;}
        [data-testid="stAlert"]{border-radius:11px;border:1px solid rgba(85,190,211,.24);background:rgba(12,31,47,.86);}
        [data-testid="stTabs"] button{color:#9bb8c8;font-weight:750;}
        [data-testid="stTabs"] button[aria-selected="true"]{color:#62eaf2;border-bottom-color:#62eaf2;}
        [data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,#9a65db,#e58be8);}
        [data-testid="stPlotlyChart"],[data-testid="stVegaLiteChart"],[data-testid="stArrowVegaLiteChart"]{
          border:1px solid rgba(85,190,211,.18);border-radius:13px;background:rgba(29,17,48,.72);padding:5px;
        }
        hr{border-color:rgba(85,190,211,.2);}
        code{color:#72eaf0;background:#10283b;border-radius:5px;}
        a{color:#62eaf2!important;}
        @media(max-width:850px){.pc-hero-grid{grid-template-columns:1fr}.pc-hero-side{display:none}.pc-hero{padding:23px 20px}.pc-title{font-size:39px}}
        @media(max-width:760px){.block-container{padding-left:1rem;padding-right:1rem}}
        /* Command-center motion layer: restrained ambient motion, no JS required. */
        @keyframes pcAmbientPulse {
          0%,100% { box-shadow:0 18px 48px rgba(0,0,0,.34),0 0 0 rgba(45,220,220,0); }
          50% { box-shadow:0 20px 52px rgba(0,0,0,.38),0 0 28px rgba(45,220,220,.10); }
        }
        @keyframes pcSignalSweep {
          0% { transform:translateX(-110%) skewX(-18deg); opacity:0; }
          18% { opacity:.18; }
          62% { opacity:.08; }
          100% { transform:translateX(260%) skewX(-18deg); opacity:0; }
        }
        .pc-hero { animation:pcAmbientPulse 8s ease-in-out infinite; }
        .pc-hero-grid { position:relative; }
        .pc-hero-grid:after {
          content:"";position:absolute;top:-28px;bottom:-26px;left:0;width:18%;
          pointer-events:none;background:linear-gradient(90deg,transparent,rgba(105,245,248,.12),transparent);
          animation:pcSignalSweep 11s ease-in-out infinite;
        }
        [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"] {
          position:relative;overflow:hidden;
        }
        [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"]:before {
          content:"";position:absolute;left:0;top:0;width:42px;height:2px;
          background:linear-gradient(90deg,#55e6f2,transparent);
          box-shadow:0 0 12px rgba(85,230,242,.65);pointer-events:none;
        }
        [data-testid="stSidebar"] [aria-current="page"] {
          background:linear-gradient(90deg,rgba(20,112,125,.30),rgba(8,40,57,.35))!important;
          border:1px solid rgba(85,230,242,.34)!important;
          box-shadow:inset 3px 0 #55e6f2;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
          font-family:"DM Mono",monospace;font-size:11px;letter-spacing:.025em;
        }
        [data-testid="stDataFrame"]:hover,[data-testid="stDataEditor"]:hover,
        [data-testid="stPlotlyChart"]:hover {
          border-color:rgba(85,230,242,.42);
          box-shadow:0 12px 30px rgba(0,0,0,.20),0 0 18px rgba(45,210,220,.07);
        }
        [data-baseweb="input"]:focus-within,[data-baseweb="select"]:focus-within,
        [data-testid="stDateInput"] input:focus,[data-testid="stNumberInput"] input:focus {
          border-color:#55e6f2!important;
          box-shadow:0 0 0 2px rgba(85,230,242,.13)!important;
        }
        @media(prefers-reduced-motion:reduce) {
          .pc-hero,.pc-hero-grid:after,[data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"] {
            animation:none!important;transition:none!important;
          }
        }
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
    st.sidebar.markdown(
        '<div style="margin:4px 10px 18px;padding:10px 11px;border-left:2px solid #35e0b3;'
        'background:rgba(10,31,46,.62);border-radius:0 8px 8px 0;">'
        '<div style="font-family:DM Mono,monospace;font-size:8px;letter-spacing:.14em;color:#7fa8bd;">'
        'APPLICATION CREATOR</div>'
        '<div style="font-size:11px;font-weight:700;color:#eaf7ff;margin-top:4px;">'
        'Agus Budianto Ulil Absyor</div></div>',
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
