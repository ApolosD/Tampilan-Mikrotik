import streamlit as st

from database.database import log_system_event
from mikrotik.actions import create_hotspot_user, delete_hotspot_user, list_hotspot_profiles
from mikrotik.monitoring import get_live_snapshot, normalize_hotspot_users
from utils.formatters import format_gb
from utils.user_filters import is_hidden_username

st.title("User manager")
st.caption("Create and manage MikroTik hotspot users, including data limit, similar to Mikhmon.")

is_admin = st.session_state.get("auth_user", {}).get("role") == "ADMIN"
if not is_admin:
    st.warning("Login sebagai Admin di sidebar untuk mengelola user hotspot.")
    st.stop()

live = st.session_state.get("live_snapshot") or get_live_snapshot()
if live["connection"]["status"] != "ONLINE":
    st.error(f"MikroTik is not online: {live['connection']['error']}")
    st.stop()

operator_name = st.session_state.get("operator", "System Operator")
profiles = list_hotspot_profiles() or ["default"]

with st.container(border=True):
    st.subheader("Create new user")
    with st.form("create_hotspot_user_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_profile = st.selectbox("Profile", profiles)
        with col_b:
            new_shared_users = st.number_input("Shared users", min_value=1, value=1, step=1)
            new_limit_total_gb = st.number_input("Data limit (GB, 0 = unlimited)", min_value=0.0, value=0.0, step=1.0)
            new_limit_uptime = st.text_input("Time limit (example: 1d, 12h, empty = unlimited)")
        new_comment = st.text_input("Comment (optional)")
        submitted = st.form_submit_button("Create user", type="primary")

    if submitted:
        try:
            create_hotspot_user(
                new_username,
                new_password,
                profile=new_profile,
                shared_users=int(new_shared_users),
                limit_uptime=new_limit_uptime,
                comment=new_comment,
                limit_total_gb=float(new_limit_total_gb),
            )
            log_system_event("USER CREATE", f"Hotspot user {new_username.strip()} created", operator_name)
            st.success(f"User {new_username.strip()} berhasil dibuat.")
            st.rerun()
        except (ValueError, RuntimeError) as error:
            st.error(str(error))

with st.container(border=True):
    st.subheader("Existing hotspot users")
    all_users = normalize_hotspot_users(live["users"], live["active_users"])
    visible_users = [item for item in all_users if not is_hidden_username(item["username"])]

    if not visible_users:
        st.info("Belum ada hotspot user di RouterOS.")
    else:
        st.caption("Geser ke samping di HP untuk melihat kolom Action.")
        with st.container(key="admin-actions-user-manager"):
            header = st.columns([1.6, 1, 1, 1, 1, 0.9])
            for col, label in zip(header, ["User", "Profile", "Quota", "Status", "Uptime limit", "Action"]):
                col.markdown(f"**{label}**")

            for item in visible_users:
                row = st.columns([1.6, 1, 1, 1, 1, 0.9])
                row[0].write(item["username"])
                row[1].write(item.get("profile") or "-")
                row[2].write(format_gb(item["quota_gb"]) if item["quota_gb"] else "Unlimited")
                row[3].write("BLOCKED" if item.get("disabled") else ("ONLINE" if item["is_online"] else "OFFLINE"))
                row[4].write(item.get("uptime") or "-")
                if row[5].button("Delete", key=f"delete_{item['username']}"):
                    try:
                        delete_hotspot_user(item["username"])
                        log_system_event("USER DELETE", f"Hotspot user {item['username']} deleted", operator_name)
                        st.success(f"User {item['username']} dihapus.")
                        st.rerun()
                    except (ValueError, RuntimeError) as error:
                        st.error(str(error))
