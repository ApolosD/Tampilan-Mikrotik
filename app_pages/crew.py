import streamlit as st
import re

from database.database import get_active_plan, get_connection
from mikrotik.actions import create_hotspot_user, delete_hotspot_user, kick_user, list_hotspot_profiles, set_user_blocked
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
        live_users = sorted({str(item.get("name", "")).strip() for item in (live.get("users", []) if live else []) if str(item.get("name", "")).strip()})
        user_options = live_users or sorted({record["User"] for record in records})

        control_tab, create_tab = st.tabs(["Control user", "Buat akun hotspot (Mikhmon style)"])

        with control_tab:
            selected_user = st.selectbox("Pilih user hotspot", user_options)
            selected_row = next((row for row in rows if row["username"] == selected_user), None)
            action_col, block_col, delete_col = st.columns(3)

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
                should_block = not bool(selected_row["blocked"]) if selected_row else True
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

            with delete_col:
                confirm_delete = st.checkbox("Konfirmasi hapus user", key=f"confirm_delete_{selected_user}")
                if st.button("Hapus user", type="primary", use_container_width=True, disabled=not confirm_delete):
                    try:
                        removed = delete_hotspot_user(selected_user)
                        if not removed:
                            st.warning(f"User {selected_user} tidak ditemukan di RouterOS.")
                        with get_connection() as connection:
                            connection.execute("DELETE FROM quota_transactions WHERE crew_id IN (SELECT crew_id FROM crew WHERE username = ?)", (selected_user,))
                            connection.execute("DELETE FROM usage_history WHERE crew_id IN (SELECT crew_id FROM crew WHERE username = ?)", (selected_user,))
                            connection.execute("DELETE FROM alerts WHERE crew_id IN (SELECT crew_id FROM crew WHERE username = ?)", (selected_user,))
                            connection.execute("DELETE FROM crew WHERE username = ?", (selected_user,))
                            connection.execute(
                                "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
                                ("ADMIN ACTION", f"Deleted hotspot user {selected_user}", st.session_state.operator),
                            )
                        st.success(f"User {selected_user} berhasil dihapus.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Hapus user gagal: {error}")

        with create_tab:
            try:
                profiles = list_hotspot_profiles()
            except Exception:
                profiles = ["default"]
            with st.form("create_hotspot_user_form"):
                new_username = st.text_input("Username hotspot")
                new_password = st.text_input("Password hotspot", type="password")
                profile = st.selectbox("Profile", profiles if profiles else ["default"])
                shared_users = st.number_input("Shared users", min_value=1, max_value=20, value=1, step=1)
                limit_uptime = st.text_input("Limit uptime (opsional)", placeholder="contoh: 1d 00:00:00")
                comment = st.text_input("Comment (opsional)")
                create_submitted = st.form_submit_button("Buat akun hotspot", type="primary")

            if create_submitted:
                username = new_username.strip()
                if not re.fullmatch(r"[A-Za-z0-9_.@-]{3,64}", username):
                    st.error("Username harus 3-64 karakter dan hanya boleh huruf, angka, . _ @ -")
                elif len(new_password.strip()) < 4:
                    st.error("Password hotspot minimal 4 karakter.")
                else:
                    try:
                        create_hotspot_user(
                            username=username,
                            password=new_password.strip(),
                            profile=profile,
                            shared_users=int(shared_users),
                            limit_uptime=limit_uptime,
                            comment=comment,
                        )
                        crew_id = "MT-" + re.sub(r"[^A-Za-z0-9_-]", "-", username)[:45]
                        with get_connection() as connection:
                            connection.execute(
                                "INSERT OR IGNORE INTO crew (crew_id, name, username, access_point, status, blocked, payment_package) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (crew_id, username, username, "Unassigned", "OFFLINE", 0, profile),
                            )
                            connection.execute(
                                "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
                                ("ADMIN ACTION", f"Created hotspot user {username} ({profile})", st.session_state.operator),
                            )
                        st.success(f"Akun hotspot {username} berhasil dibuat.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Gagal membuat akun hotspot: {error}")
elif st.session_state.auth_user["role"] != "ADMIN":
    st.info("Kick dan block user hanya tersedia untuk Admin.")

if plan["mode"] == "LIMITED":
    with st.expander("Quota display rule"):
        st.write("At the 80% threshold, actual usage remains accurate while the operator display shows 100% and BLOCKED.")
