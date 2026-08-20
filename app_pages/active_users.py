import streamlit as st

from mikrotik.monitoring import format_bytes, get_live_snapshot, normalize_hotspot_users
from utils.ui import render_records

st.title("Active users")
st.caption("Live sessions read from MikroTik Hotspot active users.")

live = st.session_state.get("live_snapshot") or get_live_snapshot()
if live["connection"]["status"] != "ONLINE":
    st.error(f"MikroTik is not online: {live['connection']['error']}")
    st.stop()

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
    user = active_by_name.get(username, {})
    session_bytes = float(active.get("bytes-in", 0) or 0) + float(active.get("bytes-out", 0) or 0)
    records.append({
        "User": username,
        "IP address": active.get("address", "-"),
        "MAC address": active.get("mac-address", "-"),
        "Uptime": active.get("uptime", "-"),
        "RX rate": active.get("rx-rate", "0"),
        "TX rate": active.get("tx-rate", "0"),
        "Session data": format_bytes(session_bytes),
        "Profile": user.get("profile", "-"),
    })

render_records(records)
