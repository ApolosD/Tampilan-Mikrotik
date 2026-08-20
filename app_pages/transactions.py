import streamlit as st

from database.database import get_active_plan, get_connection
from mikrotik.monitoring import get_live_snapshot
from quota.transactions import ensure_initial_allocations
from utils.formatters import format_gb
from utils.ui import render_records

st.title("Quota transactions")
plan = get_active_plan()
if plan["mode"] != "LIMITED":
    st.info("Quota transactions are available when the Internet mode is Limited. Unlimited mode has no monthly quota ledger.")
    st.stop()

live = st.session_state.get("live_snapshot") or get_live_snapshot()
live_usernames = None
if live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
ensure_initial_allocations(plan["start_date"], live_usernames)
st.caption(f"Monthly quota ledger · {plan['start_date']} to {plan['expiry_date']}")

with get_connection() as connection:
    rows = connection.execute(
        "SELECT qt.created_at, qt.transaction_type, qt.amount_gb, qt.reason, qt.operator, "
        "COALESCE(c.username, qt.crew_id) AS username, COALESCE(c.name, qt.crew_id) AS crew_name "
        "FROM quota_transactions qt LEFT JOIN crew c ON c.crew_id = qt.crew_id "
        "WHERE date(qt.created_at) BETWEEN date(?) AND date(?) ORDER BY qt.id DESC",
        (plan["start_date"], plan["expiry_date"]),
    ).fetchall()
if live_usernames is not None:
    rows = [row for row in rows if row["username"] in live_usernames]

with st.container(horizontal=True):
    st.metric("Transactions", len(rows), border=True)
    st.metric("Initial allocations", sum(row["transaction_type"] == "INITIAL" for row in rows), border=True)
    st.metric("Add-ons", sum(row["transaction_type"] == "ADD-ON" for row in rows), border=True)
    st.metric("Quota added", format_gb(sum(row["amount_gb"] for row in rows if row["transaction_type"] == "ADD-ON")), border=True)

records = [
    {
        "Date": row["created_at"],
        "User": row["username"],
        "Crew": row["crew_name"],
        "Type": row["transaction_type"],
        "Amount": f"{row['amount_gb']:+g} GB",
        "Reason": row["reason"],
        "Operator": row["operator"],
    }
    for row in rows
]
if records:
    render_records(records)
else:
    st.info("No quota transactions are recorded for the active period.")

with st.container(border=True):
    st.caption("This ledger is stored locally in SQLite. INITIAL records come from crew allocation; ADD-ON records are created when a top-up is submitted in Quota control.")
