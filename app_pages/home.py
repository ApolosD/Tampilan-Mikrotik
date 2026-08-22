import streamlit as st
from time import monotonic
import altair as alt

from database.database import get_active_plan, get_connection
from mikrotik.monitoring import format_memory, get_live_snapshot, interface_flow
from quota.engine import calculate_quota_status
from utils.formatters import format_gb
from utils.ui import render_records
from utils.user_filters import keep_visible_rows


def _normalize_ap_name(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _find_ap_flow(snapshot: dict, ap_name: str) -> dict | None:
    target = _normalize_ap_name(ap_name)
    for row in snapshot.get("interfaces", []):
        candidate_name = str(row.get("name", ""))
        if _normalize_ap_name(candidate_name) == target:
            return interface_flow(snapshot, candidate_name)
    return None


def _select_chart_sources(snapshot: dict, ap_rows_data: list) -> list[dict]:
    selected: list[dict] = []
    used_labels: set[str] = set()

    # Primary mapping: use AP names from local inventory and match against RouterOS interfaces.
    for row in ap_rows_data[:3]:
        label = str(row["name"])
        flow = _find_ap_flow(snapshot, label)
        if flow is not None:
            selected.append({"label": label, "flow": flow, "source": "mapped"})
            used_labels.add(label)

    interfaces = snapshot.get("interfaces", [])
    preferred = []
    fallback = []
    for row in interfaces:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        upper_name = name.upper()
        if upper_name in {"ETHER1", "BRIDGE", "LO"}:
            continue
        if any(token in upper_name for token in ("AP", "WLAN", "WIFI")):
            preferred.append(name)
        else:
            fallback.append(name)

    # Fallback mapping: use likely AP/wireless interfaces from RouterOS directly.
    for name in preferred + fallback:
        if len(selected) >= 3:
            break
        label = name
        if label in used_labels:
            continue
        flow = interface_flow(snapshot, name)
        if flow is None:
            continue
        selected.append({"label": label, "flow": flow, "source": "fallback"})
        used_labels.add(label)

    return selected


def _traffic_mbps(current: dict | None, previous: dict | None, elapsed_seconds: float) -> float:
    # No baseline yet (first sample after (re)start): report 0 instead of the whole counter total.
    if not current or previous is None or elapsed_seconds <= 0:
        return 0.0
    prev_rx = float(previous.get("rx_bytes", 0.0))
    prev_tx = float(previous.get("tx_bytes", 0.0))
    current_rx = float(current.get("rx_bytes", 0.0))
    current_tx = float(current.get("tx_bytes", 0.0))
    delta_bytes = max((current_rx - prev_rx) + (current_tx - prev_tx), 0.0)
    return round((delta_bytes * 8.0) / (elapsed_seconds * 1_000_000), 3)


def _choose_throughput_unit(max_mbps: float) -> str:
    if max_mbps < 1:
        return "Kbps"
    if max_mbps < 1000:
        return "Mbps"
    return "Gbps"


def _convert_mbps(mbps: float, unit: str) -> float:
    if unit == "Kbps":
        return mbps * 1000
    if unit == "Gbps":
        return mbps / 1000
    return mbps


def _format_throughput(mbps: float) -> str:
    unit = _choose_throughput_unit(mbps)
    value = _convert_mbps(mbps, unit)
    decimals = 1 if unit in ("Kbps", "Gbps") else 2
    return f"{value:.{decimals}f} {unit}"


def _to_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _flow_rate_mbps(flow: dict | None) -> float:
    if not flow:
        return 0.0
    rx = _to_float(flow.get("rx_rate"))
    tx = _to_float(flow.get("tx_rate"))
    # RouterOS rate fields are bits per second.
    return max((rx + tx) / 1_000_000, 0.0)

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

crew_rows = keep_visible_rows(crew_rows, username_key="username")

connection_status = live["connection"]
ap_flows = [interface_flow(live, str(row.get("name"))) for row in live.get("interfaces", []) if str(row.get("name", "")).upper().startswith("AP ")]
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
    st.metric("Crew online", online_count, border=True)
    if plan["mode"] == "LIMITED":
        st.metric("Master quota", format_gb(total_gb), border=True)
        st.metric("Remaining", format_gb(remaining_gb), border=True)
    live_ap_count = sum(flow is not None and flow["running"] and not flow["disabled"] for flow in ap_flows)
    live_ap_total = len(ap_flows) if ap_flows else len(ap_rows)
    st.metric("AP online", f"{live_ap_count}/{live_ap_total}", border=True)
    if blocked_count > 0:
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
    summary_rows = []
    detail_rows = []
    for row in crew_rows:
        record = {
            "User": row["username"],
            "IP address": row["ip_address"],
            "MAC address": row["mac_address"] or "-",
            "Data used": format_gb(row["used_gb"]),
            "Status": row["status"] if plan["mode"] == "UNLIMITED" else statuses[len(detail_rows)].status,
        }
        if plan["mode"] == "LIMITED":
            status = statuses[len(detail_rows)]
            record.update({"Quota": format_gb(status.quota_gb), "Remaining": format_gb(status.remaining_gb), "Display": f"{status.display_usage_percentage:.0f}%"})
        detail_rows.append(record)
        summary_rows.append(
            {
                "User": row["username"],
                "Data used": format_gb(row["used_gb"]),
                "Status": record["Status"],
            }
        )

    render_records(summary_rows[:8])
    with st.expander("Show detailed usage table"):
        render_records(detail_rows)

with st.container(border=True):
    st.subheader("Realtime traffic flow · 3 AP")
    st.caption("Total throughput RX + TX per AP. Auto refresh setiap 5 detik.")

    @st.fragment(run_every="5s")
    def render_ap_traffic_graph() -> None:
        snapshot = get_live_snapshot()
        st.session_state.live_snapshot = snapshot
        if snapshot["connection"]["status"] != "ONLINE":
            st.info("Grafik AP akan aktif setelah koneksi RouterOS ONLINE.")
            return

        chart_sources = _select_chart_sources(snapshot, ap_rows)
        labels = [item["label"] for item in chart_sources]
        if not labels:
            st.info("Belum ada data Access Point di database lokal.")
            return

        previous_labels = st.session_state.get("ap_graph_labels", [])
        if previous_labels != labels:
            st.session_state.ap_graph_history = []
            st.session_state.ap_graph_previous_flows = {}
        st.session_state.ap_graph_labels = labels

        source_types = {item["source"] for item in chart_sources}
        if source_types == {"mapped"}:
            st.caption("Sumber interface: AP mapping dari inventory lokal.")
        elif "mapped" in source_types:
            st.caption("Sumber interface: kombinasi AP mapping dan fallback interface RouterOS.")
        else:
            st.caption("Sumber interface: fallback interface RouterOS (nama AP lokal belum match).")

        now = monotonic()
        previous_time = st.session_state.get("ap_graph_time", now)
        elapsed_seconds = max(now - previous_time, 1.0)
        previous_flows = st.session_state.get("ap_graph_previous_flows", {})

        sample = {}
        current_flows = {}
        for source in chart_sources:
            label = source["label"]
            flow = source["flow"]
            current_flows[label] = flow
            sample[label] = _traffic_mbps(flow, previous_flows.get(label), elapsed_seconds)

        history = st.session_state.setdefault("ap_graph_history", [])
        if not history:
            history.append({name: 0.0 for name in labels})
        history.append(sample)
        del history[:-60]
        st.session_state.ap_graph_latest_sample = sample

        live_cols = st.columns(len(labels))
        for col, label in zip(live_cols, labels):
            with col:
                col.metric(label, _format_throughput(sample[label]), border=True)

        total_current = sum(sample.values())
        top_label = max(sample, key=sample.get)
        top_value = sample[top_label]
        history_peak = max((max(row.get(label, 0.0) for label in labels) for row in history), default=0.0)
        summary_left, summary_mid, summary_right = st.columns(3)
        summary_left.metric("Current total", _format_throughput(total_current), border=True)
        summary_mid.metric("Peak (last 60)", _format_throughput(history_peak), border=True)
        summary_right.metric("Top AP now", f"{top_label} · {_format_throughput(top_value)}", border=True)

        st.session_state.ap_graph_previous_flows = current_flows
        st.session_state.ap_graph_time = now

        chart_unit = _choose_throughput_unit(history_peak)
        chart_decimals = 1 if chart_unit in ("Kbps", "Gbps") else 2
        chart_points = []
        for index, row in enumerate(history):
            for label in labels:
                value = _convert_mbps(row.get(label, 0.0), chart_unit)
                chart_points.append({"sample": index, "ap": label, "value": value, "display": f"{value:.{chart_decimals}f} {chart_unit}"})

        chart = (
            alt.Chart(alt.Data(values=chart_points))
            .mark_area(line={"strokeWidth": 3}, interpolate="monotone", opacity=0.18)
            .encode(
                x=alt.X("sample:Q", title="Waktu (interval 5 detik)", axis=alt.Axis(grid=False)),
                y=alt.Y("value:Q", title=f"Throughput ({chart_unit})", scale=alt.Scale(zero=True, nice=True)),
                color=alt.Color(
                    "ap:N",
                    title="Access point",
                    scale=alt.Scale(range=["#2f6fed", "#12b3a8", "#f2994a", "#eb5757", "#9b6bf2"]),
                ),
                tooltip=[
                    alt.Tooltip("ap:N", title="AP"),
                    alt.Tooltip("sample:Q", title="Sample"),
                    alt.Tooltip("display:N", title="Throughput"),
                ],
            )
            .properties(height=340)
            .configure_view(stroke="transparent", fill="#fbfdff", cornerRadius=12)
            .configure_axis(
                labelColor="#4a5b6c",
                titleColor="#2b3e50",
                titleFontWeight=600,
                gridColor="#e9f0f7",
                domainColor="#d3e0ec",
                labelFontSize=11,
            )
            .configure_legend(labelColor="#2b3e50", titleColor="#2b3e50", orient="bottom", symbolType="stroke")
        )
        st.altair_chart(chart, use_container_width=True)

    render_ap_traffic_graph()
