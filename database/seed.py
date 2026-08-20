from datetime import date, timedelta

from config.settings import ADMIN_PASSWORD
from database.auth import hash_password
from database.database import get_connection, initialize_database


CREW_SEED = [
    ("CREW-01", "Crew 01", "crew01", "192.168.10.21", "AP-01", 100, 21, "ACTIVE"),
    ("CREW-02", "Crew 02", "crew02", "192.168.10.22", "AP-01", 75, 42, "ACTIVE"),
    ("CREW-03", "Crew 03", "crew03", "192.168.10.23", "AP-02", 50, 40, "BLOCKED"),
    ("CREW-04", "Crew 04", "crew04", "192.168.10.24", "AP-02", 50, 11, "ACTIVE"),
    ("CREW-05", "Crew 05", "crew05", "192.168.10.25", "AP-03", 40, 35, "ACTIVE"),
    ("CREW-06", "Crew 06", "crew06", "192.168.10.26", "AP-04", 25, 5, "ONLINE"),
]


def seed_database() -> None:
    initialize_database()
    today = date.today()
    start_date = today.replace(day=1)
    expiry_date = start_date + timedelta(days=30)
    with get_connection() as connection:
        crew_count = connection.execute("SELECT COUNT(*) FROM crew").fetchone()[0]
        if not crew_count:
            connection.execute(
                "INSERT INTO internet_plans "
                "(provider, package_name, mode, total_quota_gb, used_gb, start_date, expiry_date, cost) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("OceanLink", "Monthly 500 GB", "LIMITED", 500, 327.4, start_date.isoformat(), expiry_date.isoformat(), 1500000),
            )
            for crew_id, name, username, ip_address, access_point, quota, used, status in CREW_SEED:
                connection.execute(
                    "INSERT INTO crew "
                    "(crew_id, name, username, ip_address, access_point, quota_gb, used_gb, status, blocked, start_date, expiry_date, payment_package) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (crew_id, name, username, ip_address, access_point, quota, used, status, int(status == "BLOCKED"), start_date.isoformat(), expiry_date.isoformat(), "Custom allocation"),
                )
            connection.executemany(
                "INSERT INTO quota_transactions (crew_id, transaction_type, amount_gb, reason, operator, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                [(crew_id, "INITIAL", quota, "Initial custom allocation", "SYSTEM") for crew_id, _, _, _, _, quota, _, _ in CREW_SEED],
            )
        if connection.execute("SELECT COUNT(*) FROM access_points").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO access_points (name, ip_address, status, connected_clients, download_mbps, upload_mbps, uptime, signal) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("AP-01", "192.168.10.2", "ONLINE", 17, 42.5, 8.2, "12d 04:21", "-48 dBm"),
                    ("AP-02", "192.168.10.3", "ONLINE", 9, 21.1, 4.6, "8d 19:05", "-53 dBm"),
                    ("AP-03", "192.168.10.4", "OFFLINE", 0, 0, 0, "--", "--"),
                    ("AP-04", "192.168.10.5", "ONLINE", 6, 14.8, 2.9, "3d 11:42", "-61 dBm"),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM operators").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO operators (username, display_name, role, password_hash) VALUES (?, ?, ?, ?)",
                [
                    ("admin", "System Administrator", "ADMIN", hash_password(ADMIN_PASSWORD)),
                    ("operator", "Network Operator", "OPERATOR", None),
                    ("viewer", "Read-only Viewer", "VIEWER", None),
                ],
            )
        else:
            admin = connection.execute("SELECT id, password_hash FROM operators WHERE username = 'admin'").fetchone()
            if admin and not admin["password_hash"]:
                connection.execute("UPDATE operators SET password_hash = ? WHERE id = ?", (hash_password(ADMIN_PASSWORD), admin["id"]))
        if connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO alerts (crew_id, level, title, message, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                [
                    ("CREW-03", "BLOCK", "Quota threshold reached", "Crew 03 reached 80% actual usage and is blocked.",),
                    ("CREW-05", "WARNING", "Usage approaching threshold", "Crew 05 is at 87.5% of its personal allocation.",),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM system_logs").fetchone()[0] == 0:
            connection.execute(
                "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("SYSTEM ACTION", "Database initialized with Limited 500 GB plan", "SYSTEM"),
            )
