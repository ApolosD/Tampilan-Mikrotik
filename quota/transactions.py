from datetime import datetime

from database.database import get_connection


def ensure_initial_allocations(start_date: str, usernames: set[str] | None = None) -> None:
    """Create one INITIAL ledger entry per allocated crew for the active period."""
    with get_connection() as connection:
        crews = connection.execute("SELECT crew_id, quota_gb FROM crew WHERE quota_gb > 0").fetchall()
        for crew in crews:
            username_row = connection.execute("SELECT username FROM crew WHERE crew_id = ?", (crew["crew_id"],)).fetchone()
            if usernames is not None and (not username_row or username_row["username"] not in usernames):
                continue
            exists = connection.execute(
                "SELECT 1 FROM quota_transactions WHERE crew_id = ? AND transaction_type = 'INITIAL' AND date(created_at) >= date(?) LIMIT 1",
                (crew["crew_id"], start_date),
            ).fetchone()
            if not exists:
                connection.execute(
                    "INSERT INTO quota_transactions (crew_id, transaction_type, amount_gb, reason, operator, created_at) VALUES (?, 'INITIAL', ?, ?, ?, datetime('now'))",
                    (crew["crew_id"], crew["quota_gb"], "Monthly crew allocation", "SYSTEM"),
                )


def add_quota(crew_id: str, amount_gb: float, reason: str, operator: str) -> None:
    if amount_gb <= 0:
        raise ValueError("Add-on amount must be greater than zero")
    with get_connection() as connection:
        connection.execute("UPDATE crew SET quota_gb = quota_gb + ?, blocked = 0, status = 'ACTIVE' WHERE crew_id = ?", (amount_gb, crew_id))
        connection.execute(
            "INSERT INTO quota_transactions (crew_id, transaction_type, amount_gb, reason, operator, created_at) VALUES (?, 'ADD-ON', ?, ?, ?, ?)",
            (crew_id, amount_gb, reason, operator, datetime.now().isoformat(timespec="seconds")),
        )
        connection.execute(
            "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, ?)",
            ("OPERATOR ACTION", f"Added {amount_gb:g} GB to {crew_id}", operator, datetime.now().isoformat(timespec="seconds")),
        )
