import streamlit as st

from database.auth import create_operator, set_operator_active
from database.database import get_connection
from utils.ui import render_records

st.title("Security & operators")
st.caption("Kelola akses portal dan peran operator.")
with get_connection() as connection:
    rows = connection.execute("SELECT username, display_name, role, active FROM operators ORDER BY id").fetchall()
render_records([
    {"Username": row["username"], "Name": row["display_name"], "Role": row["role"], "State": "ACTIVE" if row["active"] else "DISABLED"}
    for row in rows
])

if st.session_state.auth_user["role"] == "ADMIN":
    with st.container(border=True):
        st.subheader("Buat akun user")
        with st.form("create_operator_form"):
            username = st.text_input("Username baru")
            display_name = st.text_input("Nama tampilan")
            role = st.selectbox("Role", ["ADMIN", "OPERATOR", "VIEWER"])
            password = st.text_input("Password", type="password")
            password_confirmation = st.text_input("Ulangi password", type="password")
            submitted = st.form_submit_button("Simpan akun", type="primary")
        if submitted:
            if password != password_confirmation:
                st.error("Konfirmasi password tidak cocok.")
            else:
                try:
                    create_operator(username, display_name, role, password)
                    st.success(f"Akun {username.strip()} berhasil dibuat.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

    with st.container(border=True):
        st.subheader("Status akun")
        for row in rows:
            action = "Nonaktifkan" if row["active"] else "Aktifkan"
            if st.button(f"{action} · {row['username']}", key=f"toggle_operator_{row['username']}"):
                if row["username"] == st.session_state.auth_user["username"]:
                    st.error("Akun yang sedang digunakan tidak dapat dinonaktifkan.")
                else:
                    with get_connection() as connection:
                        operator = connection.execute("SELECT id FROM operators WHERE username = ?", (row["username"],)).fetchone()
                    set_operator_active(operator["id"], not bool(row["active"]))
                    st.rerun()
else:
    st.info("Pengelolaan akun hanya tersedia untuk Admin.")

with st.container(border=True):
    st.subheader("Permission matrix")
    render_records([
        {"Role": "ADMIN", "Monitoring": "Yes", "Quota / add-on": "Yes", "Network control": "Yes", "Settings": "Yes"},
        {"Role": "OPERATOR", "Monitoring": "Yes", "Quota / add-on": "Yes", "Network control": "Limited", "Settings": "No"},
        {"Role": "VIEWER", "Monitoring": "Yes", "Quota / add-on": "No", "Network control": "No", "Settings": "No"},
    ])
