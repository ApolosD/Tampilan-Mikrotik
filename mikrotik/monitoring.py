from typing import Any
import re

from database.database import get_connection, log_system_event
from mikrotik.connection import get_connection_status, query

EXCLUDED_HOTSPOT_USERS = {"default-trial"}


def get_live_snapshot() -> dict[str, Any]:
    connection = get_connection_status()
    snapshot: dict[str, Any] = {"connection": connection, "resource": {}, "active_users": [], "users": [], "interfaces": []}
    if connection["status"] != "ONLINE":
        return snapshot
    try:
        resources = query(("system", "resource"))
        snapshot["resource"] = resources[0] if resources else {}
        snapshot["active_users"] = query(("ip", "hotspot", "active"))
        snapshot["users"] = query(("ip", "hotspot", "user"))
        snapshot["interfaces"] = query(("interface",))
    except Exception as error:
        snapshot["connection"] = {**connection, "status": "OFFLINE", "error": str(error)}
    return snapshot


def format_memory(resource: dict[str, Any]) -> str:
    total = float(resource.get("total-memory", 0) or 0)
    free = float(resource.get("free-memory", 0) or 0)
    if total <= 0:
        return "n/a"
    return f"{((total - free) / total) * 100:.0f}%"


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _bytes_to_gb(value: Any) -> float:
    return round(_number(value) / (1024**3), 3)


def normalize_hotspot_users(users: list[dict[str, Any]], active_users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_by_user = {str(item.get("user", "")): item for item in active_users}
    normalized = []
    for user in users:
        username = str(user.get("name", "")).strip()
        if not username or username.casefold() in EXCLUDED_HOTSPOT_USERS:
            continue
        active = active_by_user.get(username, {})
        used_gb = _bytes_to_gb(_number(user.get("bytes-in")) + _number(user.get("bytes-out")))
        active_used_gb = _bytes_to_gb(_number(active.get("bytes-in")) + _number(active.get("bytes-out")))
        normalized.append({
            "username": username,
            "name": username,
            "ip_address": active.get("address", user.get("address", "")),
            "mac_address": active.get("mac-address", user.get("mac-address", "")),
            "profile": user.get("profile", ""),
            "quota_gb": _bytes_to_gb(user.get("limit-bytes-total")),
            "used_gb": max(used_gb, active_used_gb),
            "is_online": username in active_by_user,
            "rx_rate": active.get("rx-rate", "0"),
            "tx_rate": active.get("tx-rate", "0"),
            "uptime": active.get("uptime", user.get("uptime", "")),
            "disabled": str(user.get("disabled", "false")).lower() == "true",
        })
    return normalized


def sync_hotspot_users(snapshot: dict[str, Any]) -> None:
    if snapshot["connection"]["status"] != "ONLINE":
        return
    users = normalize_hotspot_users(snapshot["users"], snapshot["active_users"])
    with get_connection() as connection:
        for item in users:
            existing = connection.execute("SELECT * FROM crew WHERE username = ?", (item["username"],)).fetchone()
            if existing:
                quota = item["quota_gb"] if item["quota_gb"] > 0 else existing["quota_gb"]
                connection.execute(
                    "UPDATE crew SET name = ?, ip_address = ?, mac_address = ?, used_gb = ?, quota_gb = ?, status = ?, blocked = ? WHERE username = ?",
                    (
                        item["name"], item["ip_address"], item["mac_address"], item["used_gb"], quota,
                        "ONLINE" if item["is_online"] else ("SUSPENDED" if item["disabled"] else "OFFLINE"),
                        int(existing["blocked"]), item["username"],
                    ),
                )
            else:
                crew_id = "MT-" + re.sub(r"[^A-Za-z0-9_-]", "-", item["username"])[:45]
                connection.execute(
                    "INSERT OR IGNORE INTO crew (crew_id, name, username, ip_address, mac_address, quota_gb, used_gb, access_point, status, blocked, payment_package) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (crew_id, item["name"], item["username"], item["ip_address"], item["mac_address"], item["quota_gb"], item["used_gb"], "Unassigned", "ONLINE" if item["is_online"] else "OFFLINE", 0, item["profile"]),
                )


def record_hotspot_activity(previous_users: set[str] | None, current_users: set[str]) -> None:
    if previous_users is None:
        return
    excluded = {username for username in current_users | previous_users if username.casefold() in EXCLUDED_HOTSPOT_USERS}
    current_users = current_users - excluded
    previous_users = previous_users - excluded
    for username in sorted(current_users - previous_users):
        log_system_event("HOTSPOT LOGIN", f"User {username} masuk ke hotspot", username)
    for username in sorted(previous_users - current_users):
        log_system_event("HOTSPOT LOGOUT", f"User {username} keluar dari hotspot", username)


def interface_flow(snapshot: dict[str, Any], interface_name: str) -> dict[str, Any] | None:
    """Return live link state and byte counters for a RouterOS interface."""
    for interface in snapshot.get("interfaces", []):
        if str(interface.get("name", "")) == interface_name:
            return {
                "name": interface_name,
                "type": interface.get("type", ""),
                "running": str(interface.get("running", "false")).lower() == "true" or interface.get("running") is True,
                "disabled": str(interface.get("disabled", "false")).lower() == "true" or interface.get("disabled") is True,
                "rx_bytes": _number(interface.get("rx-byte")),
                "tx_bytes": _number(interface.get("tx-byte")),
                "rx_rate": interface.get("rx-rate"),
                "tx_rate": interface.get("tx-rate"),
            }
    return None


def ap_interface_flow(snapshot: dict[str, Any], ap_name: str) -> dict[str, Any] | None:
    target = _canonical_ap_name(ap_name)
    for interface in snapshot.get("interfaces", []):
        interface_name = str(interface.get("name", ""))
        if _canonical_ap_name(interface_name) == target:
            return interface_flow(snapshot, interface_name)
    return None


def ap_interface_flows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    flows = []
    for interface in snapshot.get("interfaces", []):
        interface_name = str(interface.get("name", ""))
        if _canonical_ap_name(interface_name).startswith("AP-"):
            flow = interface_flow(snapshot, interface_name)
            if flow:
                flows.append(flow)
    return sorted(flows, key=lambda flow: flow["name"])


def _canonical_ap_name(name: str) -> str:
    normalized = re.sub(r"\s+", "", name.upper())
    match = re.fullmatch(r"AP[-_]?0*(\d+)", normalized)
    return f"AP-{int(match.group(1))}" if match else normalized


def traffic_mbps(flow: dict[str, Any] | None, previous_flow: dict[str, Any] | None = None, elapsed_seconds: float = 1.0) -> float:
    if not flow:
        return 0.0
    rx_rate = _number(flow.get("rx_rate"))
    tx_rate = _number(flow.get("tx_rate"))
    if rx_rate == 0 and tx_rate == 0 and previous_flow and elapsed_seconds > 0:
        rx_rate = max(_number(flow.get("rx_bytes")) - _number(previous_flow.get("rx_bytes")), 0) * 8 / elapsed_seconds
        tx_rate = max(_number(flow.get("tx_bytes")) - _number(previous_flow.get("tx_bytes")), 0) * 8 / elapsed_seconds
    return round((rx_rate + tx_rate) / 1_000_000, 3)


def format_bytes(value: float) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    amount = max(value, 0.0)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return "0.0 B"
