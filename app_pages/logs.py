import streamlit as st

from database.database import get_connection
from utils.ui import render_records

st.title("System logs")
st.caption("Pantau login, logout, aktivitas Hotspot, dan tindakan Admin.")

with get_connection() as connection:
    rows = connection.execute("SELECT * FROM system_logs ORDER BY id DESC").fetchall()

records = [dict(row) for row in rows]
if not records:
    st.info("No system logs recorded yet.")
else:
    categories = sorted({record["category"] for record in records})
    selected_category = st.selectbox("Filter aktivitas", ["ALL", *categories])
    if selected_category != "ALL":
        records = [record for record in records if record["category"] == selected_category]
    records = [{column.replace("_", " ").title(): value for column, value in record.items()} for record in records]
    render_records(records)
