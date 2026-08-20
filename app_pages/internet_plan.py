import streamlit as st

from database.database import get_active_plan
from utils.formatters import format_currency, format_gb

st.title("Internet plan")

plan = get_active_plan()

remaining = max(float(plan["total_quota_gb"]) - float(plan["used_gb"]), 0)
columns = st.columns(4)
columns[0].metric("Package", plan["package_name"], border=True)
columns[1].metric("Mode", plan["mode"], border=True)
columns[2].metric("Total quota", format_gb(plan["total_quota_gb"]) if plan["mode"] == "LIMITED" else "Unlimited", border=True)
columns[3].metric("Remaining", format_gb(remaining) if plan["mode"] == "LIMITED" else "No cap", border=True)

with st.container(border=True):
    st.subheader("Plan details")
    st.write(f"**Provider:** {plan['provider']}")
    st.write(f"**Mode:** {plan['mode']}  ·  **Status:** {plan['status']}")
    st.write(f"**Period:** {plan['start_date']} to {plan['expiry_date']}")
    st.write(f"**Cost:** {format_currency(plan['cost'])}")
