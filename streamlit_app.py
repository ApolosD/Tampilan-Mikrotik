import streamlit as st

from config.settings import APP_NAME
from database.auth import authenticate_operator
from database.database import get_active_plan, initialize_database, set_internet_mode
from database.database import log_system_event
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
    :root {
        --ink: #102230;
        --muted: #5e7382;
        --coral: #d65b37;
        --teal: #0f8d86;
        --paper: #f0f5fa;
        --aurora-1: rgba(79, 140, 255, 0.24);
        --aurora-2: rgba(20, 141, 134, 0.19);
        --aurora-3: rgba(214, 91, 55, 0.16);
        --glass: rgba(255, 255, 255, 0.64);
        --glass-strong: rgba(255, 255, 255, 0.82);
        --line: rgba(80, 110, 128, 0.22);
    }
    .stApp {
        background:
            radial-gradient(80rem 40rem at 110% -10%, var(--aurora-1), transparent 62%),
            radial-gradient(75rem 32rem at -5% 0%, var(--aurora-2), transparent 58%),
            radial-gradient(60rem 28rem at 50% 110%, var(--aurora-3), transparent 60%),
            linear-gradient(155deg, #edf3fa 0%, #f8fbff 44%, #eef5fc 100%);
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2230 0%, #142f41 100%);
        border-right: 1px solid rgba(183, 208, 226, 0.22);
    }
    [data-testid="stSidebar"] * { color: #edf4fa !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c0d3e1 !important; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -.01em; }
    h1 {
        font-family: "Cambria", "Times New Roman", serif;
        font-size: 2.6rem;
        margin-bottom: .15rem;
        text-shadow: 0 12px 24px rgba(16, 34, 48, 0.14);
    }
    h2, h3 { font-family: "Cambria", "Times New Roman", serif; }
    [data-testid="stMetric"] {
        background: linear-gradient(155deg, var(--glass-strong), var(--glass));
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem;
        box-shadow:
            0 14px 34px rgba(17, 50, 73, .08),
            inset 0 1px 0 rgba(255, 255, 255, .55);
        transform: translateZ(0);
        transition: transform .24s ease, box-shadow .24s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow:
            0 18px 34px rgba(17, 50, 73, .14),
            inset 0 1px 0 rgba(255, 255, 255, .6);
    }
    [data-testid="stMetricValue"] { color: var(--ink); }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 16px;
        background: linear-gradient(165deg, rgba(255,255,255,.72), rgba(243,249,255,.55));
        box-shadow: 0 12px 32px rgba(21, 57, 83, 0.06);
    }
    [data-testid="stHorizontalBlock"] {
        perspective: 1200px;
    }
    .status-chip { display: inline-block; padding: .28rem .58rem; border-radius: 999px; font-size: .74rem; font-weight: 700; letter-spacing: .04em; background: #dcebe8; color: #14645f; }
    .status-chip.blocked { background: #f3d7cf; color: #9c3925; }
    table {
        width: 100%;
        border-collapse: collapse;
        background: linear-gradient(165deg, rgba(255,255,255,.77), rgba(240,248,255,.63));
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid var(--line);
    }
    th {
        text-align: left;
        color: var(--muted);
        font-size: .72rem;
        text-transform: uppercase;
        letter-spacing: .06em;
        background: rgba(229, 240, 249, 0.9);
        padding: .72rem;
    }
    td { padding: .72rem; border-top: 1px solid rgba(173, 197, 214, 0.35); color: #26343d; font-size: .88rem; }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 12px;
        border: 1px solid rgba(42, 84, 117, 0.3);
        background: linear-gradient(160deg, #ffffff 0%, #e6f1fb 100%);
        color: #123149;
        font-weight: 600;
        transition: transform .2s ease, box-shadow .2s ease;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(18, 49, 73, 0.14);
    }
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

if "auth_user" not in st.session_state:
    st.session_state.auth_user = {"username": "guest", "display_name": "Guest Viewer", "role": "VIEWER", "active": 1}
if "operator" not in st.session_state:
    st.session_state.operator = st.session_state.auth_user.get("display_name", "Guest Viewer")

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

    is_admin = st.session_state.auth_user.get("role") == "ADMIN"
    st.divider()
    if is_admin:
        st.caption(f"Admin: {st.session_state.auth_user['display_name']}")
        if st.button("Logout Admin", use_container_width=True):
            log_system_event("AUTH LOGOUT", "Logout portal", st.session_state.auth_user["username"])
            st.session_state.auth_user = {"username": "guest", "display_name": "Guest Viewer", "role": "VIEWER", "active": 1}
            st.session_state.operator = "Guest Viewer"
            st.rerun()
    else:
        st.caption("Admin portal")
        with st.form("sidebar_admin_login"):
            admin_username = st.text_input("Username", autocomplete="username", placeholder="admin")
            admin_password = st.text_input("Password", type="password", autocomplete="current-password", placeholder="••••••")
            login_submitted = st.form_submit_button("Login Admin", type="primary", use_container_width=True)

        if login_submitted:
            username = admin_username.strip()
            password = admin_password.strip()
            if not username or not password:
                st.error("Username dan password wajib diisi.")
            else:
                operator = authenticate_operator(username, password)
                if not operator:
                    st.error("Login gagal. Periksa username dan password Admin.")
                elif operator.get("role") != "ADMIN":
                    st.error("Akun valid, tetapi bukan role Admin.")
                else:
                    st.session_state.auth_user = operator
                    st.session_state.operator = operator.get("display_name", operator.get("username", "System Operator"))
                    log_system_event("AUTH LOGIN", "Login portal berhasil", operator["username"])
                    st.success("Login Admin berhasil.")
                    st.rerun()

    st.caption("Local data · RouterOS connection enabled when configured")

page.run()
