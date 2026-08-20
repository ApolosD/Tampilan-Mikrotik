from typing import Any

from mikrotik.connection import open_connection


def kick_user(username: str) -> int:
    removed = 0
    with open_connection() as api:
        active_users = api.path("ip", "hotspot", "active")
        for user in list(active_users):
            if str(user.get("user", "")) != username:
                continue
            session_id = user.get(".id") or user.get("id")
            if session_id:
                active_users.remove(session_id)
                removed += 1
    return removed


def set_user_blocked(username: str, blocked: bool) -> None:
    with open_connection() as api:
        users = api.path("ip", "hotspot", "user")
        for user in list(users):
            if str(user.get("name", "")) != username:
                continue
            user_id = user.get(".id") or user.get("id")
            if not user_id:
                raise RuntimeError(f"ID RouterOS untuk user {username} tidak ditemukan")
            users.set(user_id, disabled="yes" if blocked else "no")
            return
    raise RuntimeError(f"User {username} tidak ditemukan di RouterOS")


def list_hotspot_profiles() -> list[str]:
    with open_connection() as api:
        profiles = api.path("ip", "hotspot", "user", "profile")
        names = sorted({str(item.get("name", "")).strip() for item in list(profiles) if str(item.get("name", "")).strip()})
    return names


def create_hotspot_user(
    username: str,
    password: str,
    profile: str = "default",
    shared_users: int = 1,
    limit_uptime: str = "",
    comment: str = "",
) -> None:
    username = username.strip()
    if not username:
        raise ValueError("Username wajib diisi")
    if not password:
        raise ValueError("Password wajib diisi")
    if shared_users < 1:
        raise ValueError("Shared users minimal 1")

    with open_connection() as api:
        users = api.path("ip", "hotspot", "user")
        existing = next((item for item in list(users) if str(item.get("name", "")) == username), None)
        if existing:
            raise RuntimeError(f"User {username} sudah ada di RouterOS")

        payload: dict[str, Any] = {
            "name": username,
            "password": password,
            "profile": profile or "default",
            "shared-users": str(shared_users),
        }
        if limit_uptime.strip():
            payload["limit-uptime"] = limit_uptime.strip()
        if comment.strip():
            payload["comment"] = comment.strip()
        users.add(**payload)


def delete_hotspot_user(username: str) -> bool:
    removed = False
    with open_connection() as api:
        active_users = api.path("ip", "hotspot", "active")
        for user in list(active_users):
            if str(user.get("user", "")) != username:
                continue
            session_id = user.get(".id") or user.get("id")
            if session_id:
                active_users.remove(session_id)

        users = api.path("ip", "hotspot", "user")
        for user in list(users):
            if str(user.get("name", "")) != username:
                continue
            user_id = user.get(".id") or user.get("id")
            if user_id:
                users.remove(user_id)
                removed = True
                break
    return removed
