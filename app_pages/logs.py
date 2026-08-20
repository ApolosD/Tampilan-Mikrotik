import streamlit as st

from database.database import get_connection
from utils.ui import render_records

st.title("System logs")
st.caption("Audit trail for system, operator, and future MikroTik events.")

with get_connection() as connection:
    rows = connection.execute("SELECT * FROM system_logs ORDER BY id DESC").fetchall()

records = [dict(row) for row in rows]
if not records:
    st.info("No system logs recorded yet.")
else:
    records = [
        {column.replace("_", " ").title(): value for column, value in record.items()}
        for record in records
    ]
    render_records(records)
