import streamlit as st

from config.settings import APP_NAME
from database.database import get_active_plan, initialize_database, set_internet_mode
from database.seed import seed_database
from mikrotik.monitoring import get_live_snapshot, sync_hotspot_users

st.set_page_config(page_title=APP_NAME, page_icon=":material/network_check:", layout="wide")

initialize_database()
seed_database()
live_snapshot = get_live_snapshot()
sync_hotspot_users(live_snapshot)
st.session_state.live_snapshot = live_snapshot

st.markdown(
    """
    <style>
    :root { --ink: #18242d; --muted: #66747d; --coral: #d05a3b; --teal: #147d78; --paper: #f7f3eb; }
    .stApp { background: radial-gradient(circle at 90% 0%, #ead6c7 0, transparent 32%), var(--paper); }
    [data-testid="stSidebar"] { background: #18242d; }
    [data-testid="stSidebar"] * { color: #f4efe6 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c8d1d0 !important; }
    h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
    h1 { font-family: Georgia, serif; font-size: 2.6rem; margin-bottom: .15rem; }
    h2, h3 { font-family: Georgia, serif; }
    [data-testid="stMetric"] { background: rgba(255,255,255,.72); border: 1px solid #e5ddd1; border-radius: 14px; padding: 1rem; box-shadow: 0 8px 24px rgba(24,36,45,.06); }
    [data-testid="stMetricValue"] { color: var(--ink); }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #e5ddd1; border-radius: 14px; background: rgba(255,255,255,.48); }
    .status-chip { display: inline-block; padding: .28rem .58rem; border-radius: 999px; font-size: .74rem; font-weight: 700; letter-spacing: .04em; background: #dcebe8; color: #14645f; }
    .status-chip.blocked { background: #f3d7cf; color: #9c3925; }
    table { width: 100%; border-collapse: collapse; background: rgba(255,255,255,.62); border-radius: 12px; overflow: hidden; }
    th { text-align: left; color: #66747d; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; background: #eee7dc; padding: .72rem; }
    td { padding: .72rem; border-top: 1px solid #eee7dc; color: #26343d; font-size: .88rem; }
    .responsive-table { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 12px; }
    .responsive-table table { min-width: 680px; }
    @media (max-width: 768px) {
        section.main > div { padding: 1rem .7rem 2.5rem; }
        h1 { font-size: 2rem; line-height: 1.08; }
        h2 { font-size: 1.45rem; }
        h3 { font-size: 1.15rem; }
        [data-testid="stMetric"] { padding: .72rem; border-radius: 11px; }
        [data-testid="stMetricLabel"] { font-size: .72rem; }
        [data-testid="stMetricValue"] { font-size: 1.45rem; }
        [data-testid="stHorizontalBlock"] { gap: .55rem !important; flex-wrap: wrap !important; }
        [data-testid="stHorizontalBlock"] > div { min-width: min(100%, 145px) !important; flex: 1 1 145px !important; }
        [data-testid="stVerticalBlockBorderWrapper"] { padding: .65rem !important; }
        .responsive-table table { min-width: 620px; }
        th { font-size: .66rem; padding: .58rem; }
        td { font-size: .78rem; padding: .58rem; }
        div.stButton > button, div.stDownloadButton > button { width: 100%; min-height: 2.7rem; }
        [data-testid="stSidebar"] { min-width: 17rem; max-width: 17rem; }
    }
    @media (max-width: 480px) {
        section.main > div { padding-left: .5rem; padding-right: .5rem; }
        [data-testid="stHorizontalBlock"] > div { min-width: 100% !important; flex-basis: 100% !important; }
        [data-testid="stMetricValue"] { font-size: 1.3rem; }
        .responsive-table table { min-width: 580px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "operator" not in st.session_state:
    st.session_state.operator = "System Operator"

page = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Overview", icon=":material/dashboard:"),
        ],
        "Management": [
            st.Page("app_pages/crew.py", title="Crew", icon=":material/group:"),
            st.Page("app_pages/active_users.py", title="Active users", icon=":material/person_search:"),
            st.Page("app_pages/devices.py", title="Devices", icon=":material/devices:"),
            st.Page("app_pages/access_points.py", title="Access points", icon=":material/wifi:"),
            st.Page("app_pages/bandwidth.py", title="Bandwidth", icon=":material/speed:"),
            st.Page("app_pages/internet_plan.py", title="Internet plan", icon=":material/data_usage:"),
            st.Page("app_pages/quota.py", title="Quota control", icon=":material/pie_chart:"),
            st.Page("app_pages/transactions.py", title="Transactions", icon=":material/receipt_long:"),
        ],
        "Intelligence": [
            st.Page("app_pages/analytics.py", title="Analytics", icon=":material/analytics:"),
            st.Page("app_pages/forecast.py", title="Forecast", icon=":material/insights:"),
            st.Page("app_pages/alerts.py", title="Alerts", icon=":material/notifications:"),
            st.Page("app_pages/reports.py", title="Reports", icon=":material/description:"),
        ],
        "Operations": [
            st.Page("app_pages/firewall.py", title="Firewall control", icon=":material/security:"),
            st.Page("app_pages/logs.py", title="System logs", icon=":material/list_alt:"),
            st.Page("app_pages/security.py", title="Security", icon=":material/admin_panel_settings:"),
            st.Page("app_pages/settings.py", title="Settings", icon=":material/settings:"),
        ],
    },
    position="sidebar",
)

with st.sidebar:
    st.caption("Internet management system")
    st.divider()
    current_plan = get_active_plan()
    selected_mode = st.segmented_control(
        "Internet mode",
        ["LIMITED", "UNLIMITED"],
        default=current_plan["mode"],
    )
    if selected_mode and selected_mode != current_plan["mode"]:
        set_internet_mode(selected_mode)
        st.rerun()
    st.caption("Local data · RouterOS connection enabled when configured")

page.run()
