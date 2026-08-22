import streamlit as st

from database.database import log_system_event
from mikrotik.actions import kick_user, set_user_blocked
from mikrotik.monitoring import format_bytes, get_live_snapshot, normalize_hotspot_users
from utils.ui import render_records
from utils.user_filters import is_hidden_username

st.title("Active users")
st.caption("Live sessions read from MikroTik Hotspot active users.")

live = st.session_state.get("live_snapshot") or get_live_snapshot()
if live["connection"]["status"] != "ONLINE":
    st.error(f"MikroTik is not online: {live['connection']['error']}")
    st.stop()

is_admin = st.session_state.get("auth_user", {}).get("role") == "ADMIN"
operator_name = st.session_state.get("operator", "System Operator")

active_users = live["active_users"]
all_users = normalize_hotspot_users(live["users"], active_users)
active_by_name = {item["username"]: item for item in all_users if item["is_online"]}

with st.container(horizontal=True):
    st.metric("Active sessions", len(active_users), border=True)
    st.metric("Known Hotspot users", len(live["users"]), border=True)
    st.metric("RouterOS", live["connection"]["version"], border=True)

records = []
for active in active_users:
    username = str(active.get("user", ""))
    if is_hidden_username(username):
        continue
    user = active_by_name.get(username, {})
    session_bytes = float(active.get("bytes-in", 0) or 0) + float(active.get("bytes-out", 0) or 0)
    records.append({
        "username": username,
        "User": username,
        "IP address": active.get("address", "-"),
        "MAC address": active.get("mac-address", "-"),
        "Uptime": active.get("uptime", "-"),
        "RX rate": active.get("rx-rate", "0"),
        "TX rate": active.get("tx-rate", "0"),
        "Session data": format_bytes(session_bytes),
        "Profile": user.get("profile", "-"),
        "blocked": bool(user.get("disabled")),
    })

if not is_admin:
    render_records([{key: value for key, value in record.items() if key not in ("username", "blocked")} for record in records])
    st.stop()

if not records:
    st.info("No records available.")
    st.stop()

header = st.columns([1.1, 1, 1, 0.9, 0.7, 0.7, 1, 0.9, 0.7, 0.7])
for col, label in zip(header, ["User", "IP address", "MAC address", "Uptime", "RX", "TX", "Session data", "Profile", "Kick", "Block"]):
    col.markdown(f"**{label}**")

for record in records:
    row = st.columns([1.1, 1, 1, 0.9, 0.7, 0.7, 1, 0.9, 0.7, 0.7])
    row[0].write(record["User"])
    row[1].write(record["IP address"])
    row[2].write(record["MAC address"])
    row[3].write(record["Uptime"])
    row[4].write(record["RX rate"])
    row[5].write(record["TX rate"])
    row[6].write(record["Session data"])
    row[7].write(record["Profile"])

    if row[8].button("Kick", key=f"kick_{record['username']}"):
        removed = kick_user(record["username"])
        log_system_event("USER KICK", f"Kicked {record['username']} ({removed} session)", operator_name)
        st.success(f"{record['username']} disconnected.")
        st.rerun()

    block_label = "Unblock" if record["blocked"] else "Block"
    if row[9].button(block_label, key=f"block_{record['username']}"):
        set_user_blocked(record["username"], not record["blocked"])
        log_system_event("USER BLOCK", f"{block_label} {record['username']}", operator_name)
        st.success(f"{record['username']} {block_label.lower()}ed.")
        st.rerun()
