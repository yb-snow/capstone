import streamlit as st

_CSS = """
<style>
/* ════════════════════════════════════════════════════════════
   Doc Agent — Global styles
   Contrast ratios target WCAG AA (≥4.5:1 normal, ≥3:1 large)
   Dark text #1a2744 on #f0f4f8 = ~9:1  ✅
   Dark text #1a2744 on #ffffff  = ~12:1 ✅
   Caption   #374151 on #f0f4f8 = ~7:1  ✅
   ════════════════════════════════════════════════════════════ */

/* ── Chrome / frame ──────────────────────────────────────── */
#MainMenu, footer, header        {visibility: hidden;}
[data-testid="stAppViewContainer"]{background: #f0f4f8;}
[data-testid="stMain"]            {background: #f0f4f8;}
.block-container                  {padding-top: 1.5rem;}

/* ── Universal text reset (main content only) ────────────── */
[data-testid="stMain"]           {color: #1a2744;}

/* Every text-bearing element in the main area */
[data-testid="stMain"] p,
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] h4,
[data-testid="stMain"] h5,
[data-testid="stMain"] h6,
[data-testid="stMain"] li,
[data-testid="stMain"] td,
[data-testid="stMain"] th,
[data-testid="stMain"] span,
[data-testid="stMain"] a,
[data-testid="stMain"] strong,
[data-testid="stMain"] em       {color: #1a2744 !important;}

/* ── Form labels ─────────────────────────────────────────── */
label,
.stTextInput  > label,
.stTextArea   > label,
.stSelectbox  > label,
.stNumberInput > label,
.stSlider     > label,
.stCheckbox   > label,
.stRadio      > label,
.stFileUploader > label,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p {
    color: #1a2744 !important;
    font-weight: 500 !important;
}

/* ── Input fields (text, number, text-area) ──────────────── */
.stTextInput  input,
.stNumberInput input,
.stTextArea   textarea {
    color:            #1a2744 !important;
    background-color: #ffffff !important;
    border:           1.5px solid #c7d2e7 !important;
    border-radius:    8px !important;
}
.stTextInput  input:focus,
.stNumberInput input:focus,
.stTextArea   textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.15) !important;
}
/* Disabled / read-only fields */
.stTextInput  input:disabled,
.stNumberInput input:disabled,
.stTextArea   textarea:disabled {
    color:            #374151 !important;
    background-color: #f1f5f9 !important;
    border-color:     #e2e8f0 !important;
}
/* Placeholder text */
.stTextInput  input::placeholder,
.stNumberInput input::placeholder,
.stTextArea   textarea::placeholder {color: #94a3b8 !important;}

/* ── Selectbox ───────────────────────────────────────────── */
[data-baseweb="select"] div,
[data-baseweb="select"] span,
[data-baseweb="select"] input {
    color:            #1a2744 !important;
    background-color: #ffffff !important;
}
[data-baseweb="select"] > div {
    border:        1.5px solid #c7d2e7 !important;
    border-radius: 8px !important;
}
/* Dropdown menu options */
[data-baseweb="popover"] li,
[data-baseweb="popover"] div,
[data-baseweb="menu"]    li    {color: #1a2744 !important; background: #ffffff !important;}
[data-baseweb="menu"]    li:hover {background: #eff6ff !important;}

/* ── Captions & helper text ──────────────────────────────── */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
small, .caption                 {color: #374151 !important;}

/* ── Markdown containers ─────────────────────────────────── */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] * {color: #1a2744 !important;}

/* ── Metric widget ───────────────────────────────────────── */
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"]  p  {color: #374151 !important; font-size:.85rem !important;}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"]  div {color: #1a2744 !important; font-weight:700 !important;}
[data-testid="stMetricDelta"],
[data-testid="stMetricDelta"]  div {color: #374151 !important;}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px       !important;
    font-weight:   600       !important;
    transition:    all .15s  !important;
    color:         #1a2744   !important;       /* default / secondary */
    background:    #ffffff   !important;
    border:        1.5px solid #c7d2e7 !important;
}
.stButton > button:hover {
    transform:    translateY(-1px);
    box-shadow:   0 4px 12px rgba(0,0,0,.12) !important;
    border-color: #2563eb !important;
}
/* Primary buttons */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    color:      #ffffff   !important;
    background: #2563eb   !important;
    border:     none      !important;
}
.stButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background: #1d4ed8 !important;
}

/* ── Tabs ────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"]   {background: transparent;}
[data-testid="stTabs"] [data-baseweb="tab"]        {color: #374151 !important; font-weight:500;}
[data-testid="stTabs"] [aria-selected="true"]      {color: #2563eb !important; font-weight:700;}
[data-testid="stTabs"] [data-baseweb="tab-border"] {background: #2563eb !important;}

/* ── Expander ────────────────────────────────────────────── */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p  {color: #1a2744 !important; font-weight:600 !important;}
[data-testid="stExpander"] details    {background: #ffffff; border-radius:8px; border:1px solid #e2e8f0;}

/* ── Alerts (info / success / warning / error) ───────────── */
[data-testid="stAlert"],
[data-testid="stAlert"] p,
[data-testid="stAlert"] div,
.stSuccess p, .stInfo p, .stWarning p, .stError p {color: #1a2744 !important;}

/* ── Data table / dataframe ──────────────────────────────── */
[data-testid="stDataFrame"]          {border-radius: 8px; overflow:hidden;}
[data-testid="stDataFrame"] *        {color: #1a2744 !important;}
[data-testid="stTable"]    td,
[data-testid="stTable"]    th        {color: #1a2744 !important;}

/* ── File uploader ───────────────────────────────────────── */
[data-testid="stFileUploader"]       {
    border:        2px dashed #c7d2e7 !important;
    border-radius: 12px !important;
    background:    #f8faff !important;
}
[data-testid="stFileUploader"] *,
[data-testid="stFileUploaderDropzone"] span {color: #374151 !important;}

/* ── Slider ──────────────────────────────────────────────── */
[data-testid="stSlider"] div[data-testid="stTickBarMin"],
[data-testid="stSlider"] div[data-testid="stTickBarMax"],
[data-testid="stSlider"] p {color: #374151 !important;}

/* ── Progress bar ────────────────────────────────────────── */
[data-testid="stProgress"] > div     {background: #e2e8f0 !important;}
[data-testid="stProgress"] > div > div {background: #2563eb !important;}

/* ── Containers / cards ──────────────────────────────────── */
[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 0;
}

/* ── Divider ─────────────────────────────────────────────── */
hr {border-color: #e2e8f0 !important;}

/* ════════════════════════════════════════════════════════════
   SIDEBAR — dark background set via config.toml (#1a2744)
   CSS here just ensures text and buttons are always visible.
   ════════════════════════════════════════════════════════════ */

/* Force all text inside sidebar to be light — belt AND braces */
[data-testid="stSidebar"],
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] a      {color: #e8edf5 !important;}

/* Nav buttons — transparent background so dark sidebar shows through */
[data-testid="stSidebar"] .stButton > button {
    color:            #e8edf5                   !important;
    background-color: rgba(255,255,255,0.07)    !important;
    border:           1px solid rgba(255,255,255,0.12) !important;
    border-radius:    8px                       !important;
    font-weight:      500                       !important;
    text-align:       left                      !important;
    padding:          8px 14px                  !important;
    margin:           2px 0                     !important;
    width:            100%                      !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255,255,255,0.15)    !important;
    border-color:     rgba(255,255,255,0.3)     !important;
    transform:        none                      !important;   /* disable lift effect in sidebar */
}

/* ── Sidebar expand / collapse buttons ───────────────────────────────────── */

/*
 * Streamlit 1.35+ uses these data-testids:
 *   stSidebarCollapsedControl  → the ▶ expand button shown when sidebar is CLOSED
 *   stSidebarCollapseButton    → the ◀ collapse button shown INSIDE the sidebar
 *
 * Older names (kept for compatibility):
 *   collapsedControl, baseButton-headerNoPadding
 */

/* ▶  EXPAND BUTTON — appears when sidebar is collapsed ───────────────────── */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display:    flex    !important;
    visibility: visible !important;
    opacity:    1       !important;
    position:   fixed   !important;
    top:        12px    !important;
    left:       12px    !important;
    z-index:    99999   !important;
    pointer-events: all !important;
}

[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button {
    display:          flex           !important;
    align-items:      center         !important;
    justify-content:  center         !important;
    visibility:       visible        !important;
    opacity:          1              !important;
    width:            40px           !important;
    height:           40px           !important;
    min-width:        40px           !important;
    background-color: #2563eb        !important;
    color:            #ffffff        !important;
    border:           none           !important;
    border-radius:    10px           !important;
    box-shadow:       0 4px 14px rgba(37,99,235,.45) !important;
    cursor:           pointer        !important;
    font-size:        1.1rem         !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="collapsedControl"] button:hover {
    background-color: #1d4ed8 !important;
    box-shadow: 0 6px 18px rgba(37,99,235,.55) !important;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg {
    fill:   #ffffff !important;
    color:  #ffffff !important;
    stroke: #ffffff !important;
    width:  18px    !important;
    height: 18px    !important;
}

/* ◀  COLLAPSE BUTTON — inside the sidebar header ─────────────────────────── */
[data-testid="stSidebarCollapseButton"]             {visibility: visible !important;}
[data-testid="stSidebarCollapseButton"] button,
button[data-testid="baseButton-headerNoPadding"]    {
    display:          flex              !important;
    visibility:       visible           !important;
    opacity:          1                 !important;
    color:            #e8edf5           !important;
    background-color: rgba(255,255,255,.1) !important;
    border:           1px solid rgba(255,255,255,.2) !important;
    border-radius:    7px               !important;
    width:            34px              !important;
    height:           34px              !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
button[data-testid="baseButton-headerNoPadding"]:hover {
    background-color: rgba(255,255,255,.22) !important;
}
[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="baseButton-headerNoPadding"] svg {
    fill:   #e8edf5 !important;
    color:  #e8edf5 !important;
    stroke: #e8edf5 !important;
}

/* ════════════════════════════════════════════════════════════
   Custom component styles
   ════════════════════════════════════════════════════════════ */

/* ── Page header ─────────────────────────────────────────── */
.page-header {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(26,39,68,.06);
    display: flex;
    align-items: center;
    gap: 12px;
}
.page-header h1 {font-size:1.4rem; font-weight:700; color:#1a2744 !important; margin:0;}
.page-header p  {font-size:.85rem; color:#374151  !important; margin:2px 0 0;}

/* ── Metric cards ────────────────────────────────────────── */
.metric-card {
    background:    #ffffff;
    border-radius: 12px;
    padding:       20px 24px;
    box-shadow:    0 2px 12px rgba(26,39,68,.08);
    border-left:   4px solid;
}
.metric-card.blue  {border-color:#2563eb;}
.metric-card.green {border-color:#16a34a;}
.metric-card.amber {border-color:#d97706;}
.metric-card.red   {border-color:#dc2626;}
.metric-label {font-size:.78rem;color:#374151;text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px;}
.metric-value {font-size:2rem;font-weight:700;color:#1a2744;line-height:1;}
.metric-delta {font-size:.78rem;margin-top:6px;}
.delta-up   {color:#16a34a;}
.delta-down {color:#dc2626;}

/* ── Pipeline stepper ────────────────────────────────────── */
.step-row  {display:flex;align-items:center;gap:0;margin:24px 0;}
.step-item {display:flex;flex-direction:column;align-items:center;flex:1;}
.step-circle {
    width:36px; height:36px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:.85rem; font-weight:700;
}
.step-done    {background:#16a34a;color:#fff !important;}
.step-active  {background:#2563eb;color:#fff !important;box-shadow:0 0 0 4px rgba(37,99,235,.2);}
.step-pending {background:#e2e8f0;color:#64748b !important;}
.step-error   {background:#dc2626;color:#fff !important;}
.step-name    {font-size:.7rem;margin-top:6px;color:#374151;text-align:center;}
.step-line    {flex:1;height:2px;background:#e2e8f0;margin-top:-18px;}
.step-line.done {background:#16a34a;}

/* ── Status badges ───────────────────────────────────────── */
.badge {
    display:inline-block; padding:3px 10px; border-radius:999px;
    font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.5px;
}
.badge-valid         {background:#dcfce7; color:#14532d !important;}
.badge-failed        {background:#fee2e2; color:#7f1d1d !important;}
.badge-corrected     {background:#fef3c7; color:#78350f !important;}
.badge-review        {background:#dbeafe; color:#1e3a8a !important;}
.badge-pending_review{background:#dbeafe; color:#1e3a8a !important;}
.badge-rejected      {background:#f3f4f6; color:#374151 !important;}

/* ── Login page ──────────────────────────────────────────── */
.login-title    {font-size:1.7rem;font-weight:700;color:#1a2744;margin:0 0 4px;}
.login-subtitle {font-size:0.9rem;color:#374151;margin-bottom:32px;}
.login-hint     {font-size:0.8rem;color:#64748b;margin-top:16px;}

/* ── Sidebar logo / user info ────────────────────────────── */
.sidebar-logo    {font-size:1.5rem;font-weight:800;letter-spacing:-.5px;padding:8px 0 4px;}
.sidebar-user    {font-size:.8rem;opacity:.7;padding-bottom:12px;
                  border-bottom:1px solid rgba(255,255,255,.12);margin-bottom:12px;}
.sidebar-section {font-size:.65rem;text-transform:uppercase;letter-spacing:1.2px;
                  opacity:.5;margin:16px 0 6px;}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def badge(text: str, kind: str) -> str:
    kind_clean = kind.replace("_", "-") if kind else "review"
    return f'<span class="badge badge-{kind_clean}">{text}</span>'


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div class="page-header">
            <span style="font-size:1.8rem">{icon}</span>
            <div><h1>{title}</h1><p>{subtitle}</p></div>
        </div>""",
        unsafe_allow_html=True,
    )
