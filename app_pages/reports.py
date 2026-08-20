import csv
import io

import streamlit as st
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from database.database import get_active_plan, get_connection
from quota.engine import calculate_quota_status

st.title("Reports")
st.caption("Download a monthly operational summary from the local database.")
plan = get_active_plan()
with get_connection() as connection:
    rows = connection.execute("SELECT name, quota_gb, used_gb, status FROM crew ORDER BY name").fetchall()
live = st.session_state.get("live_snapshot")
if live and live["connection"]["status"] == "ONLINE":
    live_usernames = {str(item.get("name", "")) for item in live["users"]}
    rows = [row for row in rows if row["name"] in live_usernames]

report = io.StringIO()
writer = csv.writer(report)
writer.writerow(["User", "Quota GB", "Actual Used GB", "Actual Usage %", "Display Usage %", "Status"])
for row in rows:
    if plan["mode"] == "LIMITED":
        status = calculate_quota_status(row["quota_gb"], row["used_gb"], blocked=row["status"] == "BLOCKED")
        writer.writerow([row["name"], status.quota_gb, status.actual_used_gb, status.actual_usage_percentage, status.display_usage_percentage, status.status])
    else:
        writer.writerow([row["name"], "Unlimited", row["used_gb"], "n/a", "n/a", row["status"]])

st.download_button("Download crew CSV", report.getvalue(), file_name="crew_usage_report.csv", mime="text/csv")

excel_buffer = io.BytesIO()
workbook = Workbook()
sheet = workbook.active
sheet.title = "Crew usage"
for row in csv.reader(io.StringIO(report.getvalue())):
    sheet.append(row)
workbook.save(excel_buffer)
st.download_button("Download crew Excel", excel_buffer.getvalue(), file_name="crew_usage_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

pdf_buffer = io.BytesIO()
pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)
pdf_table = Table(list(csv.reader(io.StringIO(report.getvalue()))), repeatRows=1)
pdf_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18242d")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d5cfc4")),
    ("FONTSIZE", (0, 0), (-1, -1), 7),
]))
pdf.build([pdf_table])
st.download_button("Download crew PDF", pdf_buffer.getvalue(), file_name="crew_usage_report.pdf", mime="application/pdf")

with st.container(border=True):
    st.subheader("Report scope")
    st.write(f"Plan: {plan['package_name']} · Mode: {plan['mode']} · Period: {plan['start_date']} to {plan['expiry_date']}")
    st.write("The CSV preserves actual usage and separately includes the operator-facing display percentage.")
