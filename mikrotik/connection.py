from contextlib import contextmanager
import socket
from time import perf_counter
from typing import Any, Iterator

import librouteros
from config.settings import MIKROTIK_HOST, MIKROTIK_PASS, MIKROTIK_PORT, MIKROTIK_USER


@contextmanager
def open_connection() -> Iterator[Any]:
    if not all((MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)):
        raise RuntimeError("MikroTik credentials are not configured")
    api = librouteros.connect(
        host=MIKROTIK_HOST,
        username=MIKROTIK_USER,
        password=MIKROTIK_PASS,
        port=MIKROTIK_PORT,
    )
    try:
        yield api
    finally:
        api.close()


def query(path: tuple[str, ...]) -> list[dict[str, Any]]:
    with open_connection() as api:
        return list(api.path(*path))


def test_connection() -> dict[str, Any]:
    started = perf_counter()
    if not all((MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)):
        return {
            "status": "CREDENTIALS REQUIRED",
            "host": MIKROTIK_HOST or "Not configured",
            "port": MIKROTIK_PORT,
            "latency_ms": None,
            "identity": "",
            "version": "",
            "error": "Set MIKROTIK_HOST, MIKROTIK_PORT, MIKROTIK_USER, and MIKROTIK_PASS.",
        }
    try:
        socket_started = perf_counter()
        with socket.create_connection((MIKROTIK_HOST, MIKROTIK_PORT), timeout=8):
            tcp_latency = round((perf_counter() - socket_started) * 1000, 1)
        resources = query(("system", "resource"))
        resource = resources[0] if resources else {}
        return {
            "status": "ONLINE",
            "host": MIKROTIK_HOST,
            "port": MIKROTIK_PORT,
            "latency_ms": round((perf_counter() - started) * 1000, 1),
            "tcp_latency_ms": tcp_latency,
            "identity": resource.get("board-name", "RouterOS"),
            "version": resource.get("version", "Unknown"),
            "error": "",
        }
    except socket.timeout:
        error = f"TCP timeout: {MIKROTIK_HOST}:{MIKROTIK_PORT} is not reachable from this server."
    except OSError as error:
        error = f"TCP connection failed to {MIKROTIK_HOST}:{MIKROTIK_PORT}: {error}"
    except Exception as error:
        error = f"RouterOS API authentication/query failed: {error}"
    return {
        "status": "OFFLINE",
        "host": MIKROTIK_HOST or "Not configured",
        "port": MIKROTIK_PORT,
        "latency_ms": None,
        "identity": "",
        "version": "",
        "error": error,
    }


def get_connection_status() -> dict[str, Any]:
    if not all((MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)):
        return {
            "configured": False,
            "status": "CREDENTIALS REQUIRED",
            "host": MIKROTIK_HOST or "Not configured",
            "port": MIKROTIK_PORT,
            "latency_ms": None,
            "identity": "",
            "version": "",
            "error": "Set MIKROTIK_HOST, MIKROTIK_PORT, MIKROTIK_USER, and MIKROTIK_PASS.",
        }
    result = test_connection()
    result["configured"] = True
    return result
