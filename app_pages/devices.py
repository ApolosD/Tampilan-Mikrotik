import streamlit as st

from database.database import get_connection
from utils.ui import render_records

st.title("Devices & sessions")
st.caption("Crew-to-device mapping for IP, MAC, AP, and online state.")
with get_connection() as connection:
    rows = connection.execute("SELECT name, username, ip_address, mac_address, device, access_point, status FROM crew ORDER BY name").fetchall()
live = st.session_state.get("live_snapshot")
if live and live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    rows = [row for row in rows if row["username"] in live_usernames]
render_records([
    {"User": row["username"], "IP": row["ip_address"], "MAC": row["mac_address"] or "-", "Device": row["device"] or "-", "AP": row["access_point"], "State": row["status"]}
    for row in rows
])
