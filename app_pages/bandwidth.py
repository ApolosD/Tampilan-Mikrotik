import streamlit as st

from database.database import get_connection
from mikrotik.monitoring import format_bytes, get_live_snapshot, mapped_ap_port_flows, starlink_interface_flow
from utils.ui import render_records

st.title("Bandwidth monitoring")
st.caption("Bandwidth is managed independently from quota and package limits.")

period = st.segmented_control("Window", ["Today", "Yesterday", "7 days", "30 days"], default="Today")
with get_connection() as connection:
    crew_rows = connection.execute("SELECT name, access_point, bandwidth_down_mbps, bandwidth_up_mbps, status FROM crew ORDER BY name").fetchall()
    ap_rows = connection.execute("SELECT name, download_mbps, upload_mbps, connected_clients FROM access_points ORDER BY name").fetchall()

live = st.session_state.get("live_snapshot") or get_live_snapshot()
router_status = live["connection"]
interface_rows = live["interfaces"]
if router_status["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    crew_rows = [row for row in crew_rows if row["name"] in live_usernames]

total_down = sum(row["download_mbps"] for row in ap_rows)
total_up = sum(row["upload_mbps"] for row in ap_rows)
upstream = starlink_interface_flow(live) if router_status["status"] == "ONLINE" else None
ap_interfaces = mapped_ap_port_flows(live) if router_status["status"] == "ONLINE" else []
with st.container(horizontal=True):
    st.metric("Current download", f"{total_down:.1f} Mbps", border=True)
    st.metric("Current upload", f"{total_up:.1f} Mbps", border=True)
    st.metric("Peak traffic", f"{(total_down + total_up) * 1.35:.1f} Mbps", border=True)
    st.metric("Window", period, border=True)

with st.container(border=True):
    st.subheader("Starlink upstream")
    if upstream:
        st.write(f"**ether1** · {'ACTIVE' if upstream['running'] and not upstream['disabled'] else 'INACTIVE'}")
        st.caption(f"RX {format_bytes(upstream['rx_bytes'])} · TX {format_bytes(upstream['tx_bytes'])}")
    else:
        st.warning("ether1 is not available from the live RouterOS interface list.")

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Traffic by access point")
        render_records([
            {"AP": row["name"], "Download": f"{row['download_mbps']:.1f} Mbps", "Upload": f"{row['upload_mbps']:.1f} Mbps", "Clients": row["connected_clients"]}
            for row in ap_rows
        ])
with right:
    with st.container(border=True):
        st.subheader("Bandwidth policy by crew")
        render_records([
            {"Crew": row["name"], "Down": f"{row['bandwidth_down_mbps']:.0f} Mbps", "Up": f"{row['bandwidth_up_mbps']:.0f} Mbps", "Status": row["status"]}
            for row in crew_rows
        ])
if router_status["status"] == "ONLINE":
    with st.container(border=True):
        st.subheader("AP flow interfaces")
        render_records([
            {
                "AP": port["label"],
                "Port": port["port"],
                "Interface": port["resolved_interface"] or "Not found",
                "State": "ACTIVE" if port["flow"] and port["flow"]["running"] and not port["flow"]["disabled"] else "INACTIVE",
                "RX total": format_bytes(port["flow"]["rx_bytes"]) if port["flow"] else "0.0 B",
                "TX total": format_bytes(port["flow"]["tx_bytes"]) if port["flow"] else "0.0 B",
            }
            for port in ap_interfaces
        ])
else:
    st.info("RouterOS interface traffic will appear here after credentials are configured and the connection test succeeds.")
