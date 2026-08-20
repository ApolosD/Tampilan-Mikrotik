from datetime import datetime
from time import monotonic

import altair as alt
import pandas as pd
import streamlit as st

from database.database import get_active_plan, get_connection
from mikrotik.monitoring import ap_interface_flow, ap_interface_flows, format_memory, get_live_snapshot, interface_flow, refresh_snapshot_interfaces, traffic_mbps
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
if connection_status["status"] == "ONLINE":
    raw_ap_names = [str(item.get("name", "")) for item in live.get("interfaces", []) if str(item.get("name", "")).upper().startswith("AP ")]
    if raw_ap_names:
        overview_ap_names = raw_ap_names[:3]
    else:
        overview_ap_names = [flow["name"] for flow in ap_interface_flows(live)[:3]]
    if not overview_ap_names:
        overview_ap_names = [str(row["name"]) for row in ap_rows[:3]]
else:
    overview_ap_names = [str(row["name"]) for row in ap_rows[:3]]

ap_flows = [ap_interface_flow(live, name) for name in overview_ap_names]
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
    live_ap_total = len(overview_ap_names) if overview_ap_names else len(ap_rows)
    st.metric("AP online", f"{live_ap_count}/{live_ap_total}", border=True)
    st.metric("Crew online", online_count, border=True)
    st.metric("Blocked", blocked_count, border=True)

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

with st.container(border=True):
    st.subheader("Realtime traffic flow · 3 AP")
    st.caption("Total RX + TX per access point, diperbarui otomatis setiap 5 detik.")

    @st.fragment(run_every="5s")
    def render_ap_traffic() -> None:
        snapshot = st.session_state.get("live_snapshot") or get_live_snapshot()
        snapshot = refresh_snapshot_interfaces(snapshot)
        st.session_state.live_snapshot = snapshot
        if snapshot["connection"]["status"] != "ONLINE":
            st.warning("Traffic realtime tersedia setelah koneksi RouterOS aktif.")
            return

        raw_ap_names = [str(item.get("name", "")) for item in snapshot.get("interfaces", []) if str(item.get("name", "")).upper().startswith("AP ")]
        chart_ap_names = raw_ap_names[:3] if raw_ap_names else [flow["name"] for flow in ap_interface_flows(snapshot)[:3]]
        if not chart_ap_names:
            chart_ap_names = [str(row["name"]) for row in ap_rows[:3]]

        sample = {"Time": datetime.now().strftime("%H:%M:%S")}
        now = monotonic()
        previous_time = st.session_state.get("ap_traffic_sample_time", now)
        elapsed_seconds = max(now - previous_time, 1.0)
        previous_flows = st.session_state.get("ap_traffic_flows", {})
        current_flows = {}

        for name in chart_ap_names:
            flow = ap_interface_flow(snapshot, name)
            current_flows[name] = flow
            sample[name] = traffic_mbps(flow, previous_flows.get(name), elapsed_seconds)

        st.session_state.ap_traffic_flows = current_flows
        st.session_state.ap_traffic_sample_time = now
        history = st.session_state.setdefault("ap_traffic_history", [])
        history.append(sample)
        del history[:-60]

        chart_frame = pd.DataFrame(history)
        series_columns = [column for column in chart_frame.columns if column != "Time"]
        if not series_columns:
            st.info("Belum ada data AP untuk divisualisasikan.")
            return

        melted = chart_frame.melt(id_vars="Time", var_name="AP", value_name="Mbps")
        palette = ["#0B3C8C", "#D95F02", "#1B7F4A"]
        chart = (
            alt.Chart(melted)
            .mark_line(strokeWidth=3)
            .encode(
                x=alt.X("Time:N", title="Waktu"),
                y=alt.Y("Mbps:Q", title="Mbps"),
                color=alt.Color("AP:N", scale=alt.Scale(range=palette)),
            )
            .properties(height=340)
        )
        st.altair_chart(chart, use_container_width=True)

    render_ap_traffic()
