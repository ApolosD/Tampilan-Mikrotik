import streamlit as st

from database.database import get_connection
from utils.ui import render_records

st.title("Alert center")
st.caption("Thresholds: 70% info, 80% automatic block, 90% critical, 100% exhausted.")
with get_connection() as connection:
    rows = connection.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()

with st.container(horizontal=True):
    st.metric("Open alerts", sum(not row["acknowledged"] for row in rows), border=True)
    st.metric("Blocking events", sum(row["level"] == "BLOCK" for row in rows), border=True)
    st.metric("Critical events", sum(row["level"] == "CRITICAL" for row in rows), border=True)
render_records([
    {"Level": row["level"], "Crew": row["crew_id"] or "SYSTEM", "Title": row["title"], "Message": row["message"], "Acknowledged": "Yes" if row["acknowledged"] else "No", "Created": row["created_at"]}
    for row in rows
])
