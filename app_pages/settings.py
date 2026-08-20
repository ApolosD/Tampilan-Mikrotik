import streamlit as st

from config.settings import DEFAULT_BLOCK_THRESHOLD, DEFAULT_QUOTA_GB
from database.database import get_setting, set_setting
from mikrotik.connection import get_connection_status, test_connection

st.title("Settings")
st.caption("Operational policies, credential state, and RouterOS connectivity.")

with st.container(border=True):
    st.subheader("Quota policy")
    is_admin = st.session_state.auth_user["role"] == "ADMIN"
    saved_quota = float(get_setting("default_quota_gb", str(DEFAULT_QUOTA_GB)))
    saved_threshold = float(get_setting("block_threshold", str(DEFAULT_BLOCK_THRESHOLD)))
    quota_gb = st.number_input("Default limited package (GB)", min_value=1.0, value=saved_quota, disabled=not is_admin)
    block_threshold = st.number_input("Auto-block threshold (%)", min_value=1.0, max_value=100.0, value=saved_threshold, disabled=not is_admin)
    st.write("Display behavior: blocked users appear as 100% exhausted while actual usage remains unchanged.")
    if st.button("Simpan setting", type="primary", disabled=not is_admin):
        set_setting("default_quota_gb", str(quota_gb))
        set_setting("block_threshold", str(block_threshold))
        st.success("Setting berhasil disimpan. Hanya Admin yang dapat mengubahnya.")
    if not is_admin:
        st.info("Setting terkunci. Akses Admin diperlukan untuk mengubahnya.")

with st.container(border=True):
    st.subheader("MikroTik connection")
    status = get_connection_status()
    st.write(f"**Status:** {status['status']}")
    st.write(f"**Host:** {status['host']}")
    st.write(f"**Port:** {status['port']}")
    if status["status"] == "ONLINE":
        st.success(f"Connected to {status['identity']} · RouterOS {status['version']} · TCP {status.get('tcp_latency_ms', 'n/a')} ms")
    elif status["status"] == "CREDENTIALS REQUIRED":
        st.warning("Configure the RouterOS credentials in .env or Streamlit Secrets.")
    else:
        st.error(status["error"])
    if st.button("Test MikroTik connection", type="primary"):
        result = test_connection()
        if result["status"] == "ONLINE":
            st.success(f"Connection successful: {result['identity']} · RouterOS {result['version']}")
        else:
            st.error(result["error"])
    st.info("Credentials belong in environment variables or Streamlit Secrets, never in source code.")
