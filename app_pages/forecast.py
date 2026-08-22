from datetime import date

import streamlit as st

from database.database import get_active_plan
from quota.forecast import calculate_forecast
from utils.formatters import format_gb

st.title("Usage forecast")
plan = get_active_plan()
if plan["mode"] != "LIMITED":
    st.info("Forecast is not applicable in Unlimited mode because there is no master quota exhaustion date.")
    st.stop()

today = date.today()
days_elapsed = max(today.day, 1)
days_in_period = 31
forecast = calculate_forecast(float(plan["used_gb"]), float(plan["total_quota_gb"]), days_elapsed, max(days_in_period - days_elapsed, 0))
with st.container(horizontal=True):
    st.metric("Average daily usage", format_gb(forecast.average_daily_gb), border=True)
    st.metric("Days to exhaustion", f"{forecast.days_until_exhaustion or 'n/a'} days", border=True)
    st.metric("Projected period usage", format_gb(forecast.projected_period_usage_gb), border=True)
if forecast.warning:
    st.warning("Current usage pace suggests the master quota may be exhausted before the period ends.")
else:
    st.success("Current usage pace is within the remaining period window.")
with st.container(border=True):
    st.subheader("Forecast basis")
    st.write(f"{format_gb(plan['used_gb'])} used across {days_elapsed} elapsed days; remaining quota is {format_gb(max(plan['total_quota_gb'] - plan['used_gb'], 0))}.")
    st.caption("The first version uses a transparent average-based forecast. Historical regression can be added after live usage snapshots are connected.")
