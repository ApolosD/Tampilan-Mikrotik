from pathlib import Path
import os

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "MikroTik Internet & Crew Management"
DEFAULT_QUOTA_GB = 500.0
DEFAULT_BLOCK_THRESHOLD = 80.0


def _setting(name: str, default: str = "") -> str:
	value = os.getenv(name, "")
	if value:
		return value
	try:
		return str(st.secrets.get(name, default))
	except Exception:
		return default


MIKROTIK_HOST = _setting("MIKROTIK_HOST")
MIKROTIK_PORT = int(_setting("MIKROTIK_PORT", "8728"))
MIKROTIK_USER = _setting("MIKROTIK_USER")
MIKROTIK_PASS = _setting("MIKROTIK_PASS")
