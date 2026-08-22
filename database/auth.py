import hashlib
import hmac
import secrets
from typing import Any

from database.database import get_connection


_PASSWORD_PREFIX = "scrypt"
_PASSWORD_LENGTH = 64


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("Password harus terdiri dari minimal 6 karakter")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=_PASSWORD_LENGTH)
    return f"{_PASSWORD_PREFIX}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        prefix, salt_hex, digest_hex = encoded.split("$", 2)
        if prefix != _PASSWORD_PREFIX:
            return False
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1, dklen=_PASSWORD_LENGTH)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def authenticate_operator(username: str, password: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, username, display_name, role, active, password_hash FROM operators WHERE lower(username) = lower(?)",
            (username.strip(),),
        ).fetchone()
    if row is None or not row["active"] or not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def create_operator(username: str, display_name: str, role: str, password: str) -> None:
    username = username.strip()
    display_name = display_name.strip()
    if not username or not display_name:
        raise ValueError("Username dan nama wajib diisi")
    if role not in {"ADMIN", "OPERATOR", "VIEWER"}:
        raise ValueError("Role tidak valid")
    password_hash = hash_password(password)
    with get_connection() as connection:
        try:
            connection.execute(
                "INSERT INTO operators (username, display_name, role, password_hash) VALUES (?, ?, ?, ?)",
                (username, display_name, role, password_hash),
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError("Username sudah digunakan") from error
            raise


def set_operator_active(operator_id: int, active: bool) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE operators SET active = ? WHERE id = ?", (int(active), operator_id))
