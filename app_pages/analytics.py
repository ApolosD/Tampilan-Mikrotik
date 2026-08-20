import streamlit as st

from database.database import get_active_plan, get_connection
from quota.engine import calculate_quota_status
from utils.formatters import format_gb
from utils.ui import render_records

st.title("Usage analytics")
plan = get_active_plan()
if plan["mode"] != "LIMITED":
    st.info("Usage analytics is available in Limited mode. Unlimited mode focuses on network traffic and system health.")
    st.stop()

with get_connection() as connection:
    rows = connection.execute("SELECT * FROM crew ORDER BY used_gb DESC").fetchall()
live = st.session_state.get("live_snapshot")
if live and live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    rows = [row for row in rows if row["username"] in live_usernames]
statuses = [calculate_quota_status(row["quota_gb"], row["used_gb"], blocked=bool(row["blocked"])) for row in rows]
with st.container(horizontal=True):
    st.metric("Total quota", format_gb(sum(row["quota_gb"] for row in rows)), border=True)
    st.metric("Total used", format_gb(sum(row["used_gb"] for row in rows)), border=True)
    st.metric("Total remaining", format_gb(sum(status.remaining_gb for status in statuses)), border=True)
    st.metric("Add-ons", format_gb(35), border=True)

records = []
for row, status in zip(rows, statuses):
    records.append({"Rank": len(records) + 1, "Crew": row["name"], "Used": format_gb(row["used_gb"]), "Actual %": f"{status.actual_usage_percentage:.1f}%", "Status": status.status})
render_records(records)
