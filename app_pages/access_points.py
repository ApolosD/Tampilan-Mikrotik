import streamlit as st

from database.database import get_connection
from mikrotik.monitoring import format_bytes, get_live_snapshot, interface_flow
from utils.ui import render_records

st.title("Access points")
st.caption("AP inventory, connected clients, signal health, and current traffic.")

live = st.session_state.get("live_snapshot") or get_live_snapshot()
interface_rows = [row for row in live.get("interfaces", []) if str(row.get("name", "")).upper().startswith("AP ")]
if live["connection"]["status"] == "ONLINE" and interface_rows:
    records = []
    for interface in interface_rows:
        flow = interface_flow(live, str(interface.get("name")))
        records.append({
            "Interface": interface.get("name"),
            "State": "ONLINE" if flow and flow["running"] and not flow["disabled"] else "OFFLINE",
            "RX total": format_bytes(flow["rx_bytes"]) if flow else "0.0 B",
            "TX total": format_bytes(flow["tx_bytes"]) if flow else "0.0 B",
        })
    online = sum(record["State"] == "ONLINE" for record in records)
    clients = "From Hotspot"
else:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM access_points ORDER BY name").fetchall()
    records = [{"Interface": row["name"], "State": row["status"], "RX total": "n/a", "TX total": "n/a"} for row in rows]
    online = sum(row["status"] == "ONLINE" for row in rows)
    clients = sum(row["connected_clients"] for row in rows)

with st.container(horizontal=True):
    st.metric("AP online", f"{online}/{len(records)}", border=True)
    st.metric("Connected clients", clients, border=True)
    st.metric("Traffic source", "RouterOS interfaces" if interface_rows else "Local mapping", border=True)
render_records(records)
