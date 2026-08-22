import streamlit as st

from utils.ui import render_records

st.title("Firewall & network control")
st.caption("Live RouterOS control surface. Actions remain permission-gated until connection validation succeeds.")
with st.container(horizontal=True):
    st.metric("Address lists", 3, border=True)
    st.metric("Active rules", 12, border=True)
    st.metric("Network isolation", "Ready", border=True)

render_records([
    {"List": "blocked_crew", "Entries": 3, "Purpose": "Quota auto-block", "State": "MONITORED"},
    {"List": "suspended", "Entries": 1, "Purpose": "Administrative suspension", "State": "MONITORED"},
    {"List": "network_isolation", "Entries": 0, "Purpose": "Emergency isolation", "State": "READY"},
])
st.warning("Block, unblock, disconnect, and address-list mutations will require authenticated operator permissions and a live MikroTik connection.")
