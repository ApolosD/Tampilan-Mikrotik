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
