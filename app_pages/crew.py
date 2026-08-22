import streamlit as st

from database.database import get_active_plan, get_connection
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

if plan["mode"] == "LIMITED":
    with st.expander("Quota display rule"):
        st.write("At the 80% threshold, actual usage remains accurate while the operator display shows 100% and BLOCKED.")
