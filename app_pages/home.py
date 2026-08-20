from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import get_active_plan, get_connection
from mikrotik.monitoring import ap_interface_flow, format_memory, get_live_snapshot, interface_flow, record_hotspot_activity, sync_hotspot_users, traffic_mbps
from quota.engine import calculate_quota_status
from utils.formatters import format_gb
from utils.ui import render_records

st.title("Network overview")
st.caption("A single operating view for internet, crew, quota, and network readiness.")

plan = get_active_plan()
live = st.session_state.get("live_snapshot")
if live is None:
    live = get_live_snapshot()
with get_connection() as connection:
    crew_rows = connection.execute("SELECT * FROM crew ORDER BY crew_id").fetchall()
    ap_rows = connection.execute("SELECT * FROM access_points ORDER BY name").fetchall()

if live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    crew_rows = [row for row in crew_rows if row["username"] in live_usernames]

connection_status = live["connection"]
ap_names = [str(row["name"]) for row in ap_rows[:3]]
ap_flows = [ap_interface_flow(live, name) for name in ap_names]
upstream_flow = interface_flow(live, "ether1")
statuses = [calculate_quota_status(row["quota_gb"], row["used_gb"], blocked=bool(row["blocked"])) for row in crew_rows] if plan["mode"] == "LIMITED" else []

used_gb = float(plan["used_gb"])
total_gb = float(plan["total_quota_gb"])
remaining_gb = max(total_gb - used_gb, 0)
blocked_count = sum(status.status == "BLOCKED" for status in statuses) if plan["mode"] == "LIMITED" else sum(row["status"] == "SUSPENDED" for row in crew_rows)
online_count = len(live["active_users"]) if connection_status["status"] == "ONLINE" else sum(row["status"] == "ONLINE" for row in crew_rows)

with st.container(horizontal=True):
    st.metric("MikroTik", connection_status["status"], border=True)
    st.metric("Internet mode", plan["mode"], border=True)
    if plan["mode"] == "LIMITED":
        st.metric("Master quota", format_gb(total_gb), border=True)
        st.metric("Remaining", format_gb(remaining_gb), border=True)
    else:
        st.metric("Network policy", "No quota cap", border=True)
        st.metric("Traffic state", "Monitoring", border=True)
    live_ap_count = sum(flow is not None and flow["running"] and not flow["disabled"] for flow in ap_flows)
    live_ap_total = len(ap_flows) if ap_flows else len(ap_rows)
    st.metric("AP online", f"{live_ap_count}/{live_ap_total}", border=True)
    st.metric("Crew online", online_count, border=True)
    st.metric("Blocked", blocked_count, border=True)


with st.container(border=True):
    st.subheader("Realtime traffic flow · 3 AP")
    st.caption("Total RX + TX per access point, diperbarui otomatis setiap 5 detik.")

    @st.fragment(run_every="5s")
    def render_ap_traffic() -> None:
        snapshot = get_live_snapshot()
        if snapshot["connection"]["status"] != "ONLINE":
            st.warning("Traffic realtime tersedia setelah koneksi RouterOS aktif.")
            return
        active_users = {str(item.get("user", "")) for item in snapshot["active_users"] if item.get("user")}
        record_hotspot_activity(st.session_state.get("active_hotspot_users"), active_users)
        st.session_state.active_hotspot_users = active_users
        st.session_state.live_snapshot = snapshot
        sync_hotspot_users(snapshot)
        sample = {"Time": datetime.now().strftime("%H:%M:%S")}
        for name in ap_names:
            sample[name] = traffic_mbps(ap_interface_flow(snapshot, name))
        history = st.session_state.setdefault("ap_traffic_history", [])
        history.append(sample)
        del history[:-60]
        chart = pd.DataFrame(history).set_index("Time")
        st.line_chart(chart, y_label="Mbps", height=300)

    render_ap_traffic()

left, right = st.columns(2)
with left:
    with st.container(border=True):
        if plan["mode"] == "LIMITED":
            st.subheader("Master quota")
            st.progress(min(used_gb / total_gb, 1.0) if total_gb else 0.0)
            st.write(f"{format_gb(used_gb)} used of {format_gb(total_gb)}")
            st.caption("Actual package usage is separate from each crew's display status.")
        else:
            st.subheader("Unlimited network")
            st.markdown("### :material/all_inclusive: Open access")
            st.caption("Quota deductions, warnings, and automatic quota blocking are paused in this mode.")

with right:
    with st.container(border=True):
        st.subheader("Crew status")
        status_counts = {}
        for row in crew_rows:
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        for status, count in sorted(status_counts.items()):
            st.write(f"**{status}** · {count} crew")
        if connection_status["status"] == "ONLINE":
            resource = live["resource"]
            st.caption(f"RouterOS {connection_status['version']} · CPU {resource.get('cpu-load', 'n/a')}% · RAM {format_memory(resource)} · Uptime {resource.get('uptime', 'n/a')}")
            st.caption(f"Starlink upstream ether1: {'ACTIVE' if upstream_flow and upstream_flow['running'] and not upstream_flow['disabled'] else 'INACTIVE'}")
        else:
            st.caption(connection_status["error"])

with st.container(border=True):
    st.subheader("Usage by crew")
    table = []
    for row in crew_rows:
        record = {
            "User": row["username"],
            "IP address": row["ip_address"],
            "MAC address": row["mac_address"] or "-",
            "Data used": format_gb(row["used_gb"]),
            "Status": row["status"] if plan["mode"] == "UNLIMITED" else statuses[len(table)].status,
        }
        if plan["mode"] == "LIMITED":
            status = statuses[len(table)]
            record.update({"Quota": format_gb(status.quota_gb), "Remaining": format_gb(status.remaining_gb), "Display": f"{status.display_usage_percentage:.0f}%"})
        table.append(record)
    render_records(table)
