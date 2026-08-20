import streamlit as st

from database.database import get_active_plan, get_connection
from mikrotik.actions import kick_user, set_user_blocked
from quota.engine import calculate_quota_status
from utils.formatters import format_gb
from utils.ui import render_records

st.title("Crew management")
st.caption("Profile, device mapping, bandwidth policy, and quota state in one operational table.")
plan = get_active_plan()
live = st.session_state.get("live_snapshot")

with get_connection() as connection:
    rows = connection.execute("SELECT * FROM crew ORDER BY crew_id").fetchall()

if live and live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    rows = [row for row in rows if row["username"] in live_usernames]

records = []
for row in rows:
    status = calculate_quota_status(row["quota_gb"], row["used_gb"], blocked=bool(row["blocked"])) if plan["mode"] == "LIMITED" else None
    record = {
        "User": row["username"],
        "IP address": row["ip_address"],
        "MAC address": row["mac_address"] or "-",
        "AP": row["access_point"],
        "Data used": format_gb(row["used_gb"]),
        "Status": row["status"] if plan["mode"] == "UNLIMITED" else status.status,
        "Bandwidth": f"{row['bandwidth_down_mbps']:.0f}/{row['bandwidth_up_mbps']:.0f} Mbps",
    }
    if plan["mode"] == "LIMITED":
        record.update({"Quota": format_gb(status.quota_gb), "Actual used": format_gb(status.actual_used_gb), "Remaining": format_gb(status.remaining_gb), "Actual %": f"{status.actual_usage_percentage:.1f}%", "Display %": f"{status.display_usage_percentage:.1f}%"})
    records.append(record)

filter_status = st.pills("Filter status", ["ALL", "ACTIVE", "BLOCKED", "ONLINE", "WARNING"], default="ALL")
if filter_status != "ALL":
    records = [record for record in records if record["Status"] == filter_status]
render_records(records)

if st.session_state.auth_user["role"] == "ADMIN" and records:
    with st.container(border=True):
        st.subheader("Admin network control")
        selected_user = st.selectbox("Select user", [record["User"] for record in records])
        action_col, block_col = st.columns(2)
        with action_col:
            if st.button("Kick active session", use_container_width=True):
                try:
                    removed = kick_user(selected_user)
                    with get_connection() as connection:
                        connection.execute(
                            "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
                            ("ADMIN ACTION", f"Kicked {selected_user} ({removed} session)", st.session_state.operator),
                        )
                    st.success(f"{removed} sesi {selected_user} berhasil di-kick.")
                except Exception as error:
                    st.error(f"Kick gagal: {error}")
        with block_col:
            selected_row = next(row for row in rows if row["username"] == selected_user)
            should_block = not bool(selected_row["blocked"])
            action_label = "Block user" if should_block else "Unblock user"
            if st.button(action_label, use_container_width=True):
                try:
                    set_user_blocked(selected_user, should_block)
                    with get_connection() as connection:
                        connection.execute(
                            "UPDATE crew SET blocked = ?, status = ? WHERE username = ?",
                            (int(should_block), "BLOCKED" if should_block else "ACTIVE", selected_user),
                        )
                        connection.execute(
                            "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
                            ("ADMIN ACTION", f"{'Blocked' if should_block else 'Unblocked'} {selected_user}", st.session_state.operator),
                        )
                    st.success(f"{selected_user} berhasil di{'block' if should_block else 'unblock'}.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Perubahan status gagal: {error}")
elif st.session_state.auth_user["role"] != "ADMIN":
    st.info("Kick dan block user hanya tersedia untuk Admin.")

if plan["mode"] == "LIMITED":
    with st.expander("Quota display rule"):
        st.write("At the 80% threshold, actual usage remains accurate while the operator display shows 100% and BLOCKED.")
