from html import escape
from typing import Any

import streamlit as st


def render_records(records: list[dict[str, Any]]) -> None:
    """Render small operational tables without Streamlit's pandas-backed dataframe."""
    if not records:
        st.info("No records available.")
        return

    headers = list(records[0])
    header_html = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    rows_html = "".join(
        "<tr>"
        + "".join(f"<td>{escape(str(record.get(header, '')))}</td>" for header in headers)
        + "</tr>"
        for record in records
    )
    st.markdown(
        f"""
        <div class="responsive-table">
            <table>
                <thead><tr>{header_html}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )