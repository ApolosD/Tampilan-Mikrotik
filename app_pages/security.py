import streamlit as st

from database.database import get_connection
from utils.ui import render_records

st.title("Security & operators")
st.caption("Role model prepared for Admin, Operator, and Viewer access.")
with get_connection() as connection:
    rows = connection.execute("SELECT username, display_name, role, active FROM operators ORDER BY id").fetchall()
render_records([
    {"Username": row["username"], "Name": row["display_name"], "Role": row["role"], "State": "ACTIVE" if row["active"] else "DISABLED"}
    for row in rows
])
with st.container(border=True):
    st.subheader("Permission matrix")
    render_records([
        {"Role": "ADMIN", "Monitoring": "Yes", "Quota / add-on": "Yes", "Network control": "Yes", "Settings": "Yes"},
        {"Role": "OPERATOR", "Monitoring": "Yes", "Quota / add-on": "Yes", "Network control": "Limited", "Settings": "No"},
        {"Role": "VIEWER", "Monitoring": "Yes", "Quota / add-on": "No", "Network control": "No", "Settings": "No"},
    ])
