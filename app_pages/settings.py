import streamlit as st

from config.settings import DEFAULT_BLOCK_THRESHOLD, DEFAULT_QUOTA_GB
from mikrotik.connection import get_connection_status, test_connection

st.title("Settings")
st.caption("Operational policies, credential state, and RouterOS connectivity.")

with st.container(border=True):
    st.subheader("Quota policy")
    st.number_input("Default limited package (GB)", value=DEFAULT_QUOTA_GB, disabled=True)
    st.number_input("Auto-block threshold (%)", value=DEFAULT_BLOCK_THRESHOLD, disabled=True)
    st.write("Display behavior: blocked users appear as 100% exhausted while actual usage remains unchanged.")

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
