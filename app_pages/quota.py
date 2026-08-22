import streamlit as st

from database.database import get_active_plan, get_connection
from quota.allocation import allocation_summary, equal_allocation
from quota.transactions import add_quota
from utils.formatters import format_gb
from utils.ui import render_records
from utils.user_filters import is_hidden_username

st.title("Quota control")
plan = get_active_plan()
if plan["mode"] != "LIMITED":
    st.info("Quota management is paused in Unlimited mode. Switch the mode in the sidebar to use allocation, alerts, and add-ons.")
    st.stop()

with get_connection() as connection:
    rows = connection.execute("SELECT crew_id, name, quota_gb, used_gb, blocked FROM crew ORDER BY crew_id").fetchall()
live = st.session_state.get("live_snapshot")
if live and live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    rows = [row for row in rows if row["crew_id"].replace("MT-", "") in live_usernames or row["name"] in live_usernames]

rows = [row for row in rows if not is_hidden_username(str(row["name"])) and not is_hidden_username(str(row["crew_id"]).replace("MT-", ""))]

allocation_mode = st.segmented_control("Allocation model", ["Custom", "Equal", "Shared pool"], default="Custom")
if allocation_mode == "Equal":
    st.info(f"Equal allocation preview: {format_gb(equal_allocation(plan['total_quota_gb'], len(rows)))} per crew.")
elif allocation_mode == "Shared pool":
    st.info("Shared pool preview: crew draw from the master quota. Personal limits remain available for future policy rules.")
summary = allocation_summary(plan["total_quota_gb"], [row["quota_gb"] for row in rows])
with st.container(horizontal=True):
    st.metric("Master quota", format_gb(summary["total_quota_gb"]), border=True)
    st.metric("Allocated", format_gb(summary["allocated_gb"]), border=True)
    st.metric("Unallocated", format_gb(summary["unallocated_gb"]), border=True)

with st.container(border=True):
    st.subheader("Allocation ledger")
    render_records([
        {"Crew": row["name"], "Quota": format_gb(row["quota_gb"]), "Used": format_gb(row["used_gb"]), "Available": format_gb(max(row["quota_gb"] - row["used_gb"], 0))}
        for row in rows
    ])

with st.container(border=True):
    st.subheader("Add quota / top-up")
    with st.form("add_quota"):
        crew_id = st.selectbox("Crew", [row["crew_id"] for row in rows])
        amount = st.number_input("Add-on amount (GB)", min_value=1.0, value=10.0, step=1.0)
        reason = st.text_input("Reason", value="Operational requirement")
        submitted = st.form_submit_button("Record add-on")
    if submitted:
        add_quota(crew_id, amount, reason, st.session_state.operator)
        st.success(f"{amount:g} GB added to {crew_id}. The transaction and audit log were recorded.")
        st.rerun()
