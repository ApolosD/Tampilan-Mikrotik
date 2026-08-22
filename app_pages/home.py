import streamlit as st
from time import monotonic

from database.database import get_active_plan, get_connection
from mikrotik.monitoring import format_memory, get_live_snapshot, interface_flow
from quota.engine import calculate_quota_status
from utils.formatters import format_gb
from utils.ui import render_records


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
    if not current or elapsed_seconds <= 0:
        return 0.0
    prev_rx = float(previous.get("rx_bytes", 0.0)) if previous else 0.0
    prev_tx = float(previous.get("tx_bytes", 0.0)) if previous else 0.0
    current_rx = float(current.get("rx_bytes", 0.0))
    current_tx = float(current.get("tx_bytes", 0.0))
    delta_bytes = max((current_rx - prev_rx) + (current_tx - prev_tx), 0.0)
    return round((delta_bytes * 8.0) / (elapsed_seconds * 1_000_000), 3)

st.title("Network overview")
st.caption("A single operating view for internet, crew, quota, and network readiness.")

st.markdown(
    """
    <style>
    .spatial-hero {
        position: relative;
        overflow: hidden;
        isolation: isolate;
        border-radius: 20px;
        border: 1px solid rgba(88, 124, 151, 0.28);
        background:
            radial-gradient(40rem 20rem at 92% -24%, rgba(86, 145, 255, 0.32), transparent 60%),
            radial-gradient(35rem 16rem at -8% 100%, rgba(17, 160, 152, 0.22), transparent 60%),
            linear-gradient(145deg, rgba(245, 251, 255, 0.9) 0%, rgba(230, 241, 252, 0.84) 100%);
        padding: 1.25rem 11.75rem 1.1rem 1.25rem;
        min-height: 154px;
        margin-bottom: 1.1rem;
        box-shadow: 0 20px 40px rgba(16, 48, 71, 0.14);
    }
    .spatial-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(rgba(121, 151, 173, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(121, 151, 173, 0.15) 1px, transparent 1px);
        background-size: 22px 22px;
        opacity: .33;
        mask-image: radial-gradient(circle at 50% 20%, black 0%, transparent 76%);
    }
    .spatial-hero h3 {
        position: relative;
        z-index: 2;
        margin: 0;
        font-size: 1.3rem;
        color: #122f45;
        letter-spacing: .01em;
    }
    .spatial-hero p {
        position: relative;
        z-index: 2;
        margin: .4rem 0 0;
        color: #3d6078;
        font-size: .93rem;
    }
    .depth-stack {
        position: absolute;
        right: 1rem;
        top: 1rem;
        width: 170px;
        height: 96px;
        perspective: 1100px;
        z-index: 1;
        pointer-events: none;
    }
    .depth-plane {
        position: absolute;
        inset: 0;
        border-radius: 14px;
        border: 1px solid rgba(82, 125, 153, 0.26);
        background: linear-gradient(140deg, rgba(255,255,255,.78), rgba(213,235,254,.58));
        backdrop-filter: blur(2px);
    }
    .depth-plane.one { transform: rotateX(56deg) rotateZ(-24deg) translate3d(0, 12px, 0); opacity: .56; }
    .depth-plane.two { transform: rotateX(56deg) rotateZ(-24deg) translate3d(-8px, 2px, 0); opacity: .75; }
    .depth-plane.three { transform: rotateX(56deg) rotateZ(-24deg) translate3d(-16px, -8px, 0); opacity: .92; }
    .spatial-kpi-grid {
        position: relative;
        z-index: 2;
        display: grid;
        grid-template-columns: repeat(4, minmax(120px, 1fr));
        gap: .7rem;
        margin-top: .9rem;
    }
    .spatial-kpi {
        border-radius: 14px;
        border: 1px solid rgba(78, 117, 143, 0.32);
        background: linear-gradient(165deg, rgba(255,255,255,.88), rgba(232,244,255,.68));
        padding: .65rem .72rem;
        transform-style: preserve-3d;
        transform: translateZ(0);
        box-shadow: 0 8px 20px rgba(16, 54, 80, 0.1);
    }
    .spatial-kpi span { display: block; color: #567188; font-size: .72rem; letter-spacing: .03em; }
    .spatial-kpi strong { color: #112f45; font-size: 1rem; }
    @media (max-width: 768px) {
        .spatial-hero { padding-right: 1.1rem; min-height: auto; }
        .depth-stack { display: none; }
        .spatial-kpi-grid { grid-template-columns: repeat(2, minmax(110px, 1fr)); }
    }
    @media (max-width: 480px) {
        .spatial-kpi-grid { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
ap_flows = [interface_flow(live, str(row.get("name"))) for row in live.get("interfaces", []) if str(row.get("name", "")).upper().startswith("AP ")]
upstream_flow = interface_flow(live, "ether1")
statuses = [calculate_quota_status(row["quota_gb"], row["used_gb"], blocked=bool(row["blocked"])) for row in crew_rows] if plan["mode"] == "LIMITED" else []

used_gb = float(plan["used_gb"])
total_gb = float(plan["total_quota_gb"])
remaining_gb = max(total_gb - used_gb, 0)
blocked_count = sum(status.status == "BLOCKED" for status in statuses) if plan["mode"] == "LIMITED" else sum(row["status"] == "SUSPENDED" for row in crew_rows)
online_count = len(live["active_users"]) if connection_status["status"] == "ONLINE" else sum(row["status"] == "ONLINE" for row in crew_rows)

router_label = connection_status["status"]
plan_label = plan["mode"]
upstream_label = "ACTIVE" if upstream_flow and upstream_flow["running"] and not upstream_flow["disabled"] else "INACTIVE"

st.markdown(
    f"""
    <section class="spatial-hero">
        <div class="depth-stack" aria-hidden="true">
            <div class="depth-plane one"></div>
            <div class="depth-plane two"></div>
            <div class="depth-plane three"></div>
        </div>
        <h3>Spatial command surface</h3>
        <p>Live state dari RouterOS, quota, dan AP ditampilkan sebagai satu lapisan operasional dengan depth visual.</p>
        <div class="spatial-kpi-grid">
            <div class="spatial-kpi"><span>Router</span><strong>{router_label}</strong></div>
            <div class="spatial-kpi"><span>Internet mode</span><strong>{plan_label}</strong></div>
            <div class="spatial-kpi"><span>Crew online</span><strong>{online_count}</strong></div>
            <div class="spatial-kpi"><span>Upstream</span><strong>{upstream_label}</strong></div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

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

        live_cols = st.columns(len(labels))
        for col, label in zip(live_cols, labels):
            with col:
                col.metric(label, f"{sample[label]:.3f} Mbps", border=True)

        st.session_state.ap_graph_previous_flows = current_flows
        st.session_state.ap_graph_time = now

        history = st.session_state.setdefault("ap_graph_history", [])
        if not history:
            history.append({name: 0.0 for name in labels})
        history.append(sample)
        del history[:-60]

        chart_data = {label: [row.get(label, 0.0) for row in history] for label in labels}
        st.line_chart(chart_data, use_container_width=True, height=280)

    render_ap_traffic_graph()
