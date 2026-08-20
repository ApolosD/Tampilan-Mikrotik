from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "mikrotik_dashboard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS internet_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    package_name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('UNLIMITED', 'LIMITED')),
    total_quota_gb REAL NOT NULL DEFAULT 0,
    used_gb REAL NOT NULL DEFAULT 0,
    start_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    cost REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE IF NOT EXISTS crew (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    mac_address TEXT,
    device TEXT,
    access_point TEXT,
    quota_gb REAL NOT NULL DEFAULT 0,
    used_gb REAL NOT NULL DEFAULT 0,
    bandwidth_down_mbps REAL NOT NULL DEFAULT 0,
    bandwidth_up_mbps REAL NOT NULL DEFAULT 0,
    payment_package TEXT,
    start_date TEXT,
    expiry_date TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    blocked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS quota_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount_gb REAL NOT NULL,
    reason TEXT,
    operator TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id TEXT NOT NULL,
    used_gb REAL NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    operator TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS access_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    status TEXT NOT NULL DEFAULT 'OFFLINE',
    connected_clients INTEGER NOT NULL DEFAULT 0,
    download_mbps REAL NOT NULL DEFAULT 0,
    upload_mbps REAL NOT NULL DEFAULT 0,
    uptime TEXT,
    signal TEXT
);
CREATE TABLE IF NOT EXISTS bandwidth_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    scope_name TEXT NOT NULL,
    download_mbps REAL NOT NULL DEFAULT 0,
    upload_mbps REAL NOT NULL DEFAULT 0,
    recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id TEXT,
    level TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'OPERATOR', 'VIEWER')),
    active INTEGER NOT NULL DEFAULT 1,
    password_hash TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)
        operator_columns = {row[1] for row in connection.execute("PRAGMA table_info(operators)")}
        if "password_hash" not in operator_columns:
            connection.execute("ALTER TABLE operators ADD COLUMN password_hash TEXT")


def get_active_plan() -> sqlite3.Row:
    with get_connection() as connection:
        plan = connection.execute("SELECT * FROM internet_plans ORDER BY id DESC LIMIT 1").fetchone()
    if plan is None:
        raise RuntimeError("No internet plan is configured")
    return plan


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as connection:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as connection:
        connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))


def log_system_event(category: str, message: str, operator: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
            (category, message, operator),
        )


def set_internet_mode(mode: str) -> None:
    if mode not in {"UNLIMITED", "LIMITED"}:
        raise ValueError("Internet mode must be UNLIMITED or LIMITED")
    with get_connection() as connection:
        if mode == "UNLIMITED":
            current = connection.execute("SELECT total_quota_gb, used_gb, package_name FROM internet_plans ORDER BY id DESC LIMIT 1").fetchone()
            if current:
                connection.executemany(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    [
                        ("limited_total_quota_gb", str(current["total_quota_gb"])),
                        ("limited_used_gb", str(current["used_gb"])),
                        ("limited_package_name", current["package_name"]),
                    ],
                )
            connection.execute(
                "UPDATE internet_plans SET mode = ?, total_quota_gb = 0, used_gb = 0, package_name = ?",
                (mode, "Unlimited Internet"),
            )
        else:
            saved_total = connection.execute("SELECT value FROM settings WHERE key = 'limited_total_quota_gb'").fetchone()
            saved_used = connection.execute("SELECT value FROM settings WHERE key = 'limited_used_gb'").fetchone()
            saved_package = connection.execute("SELECT value FROM settings WHERE key = 'limited_package_name'").fetchone()
            connection.execute(
                "UPDATE internet_plans SET mode = ?, total_quota_gb = ?, used_gb = ?, package_name = ?",
                (
                    mode,
                    float(saved_total["value"]) if saved_total else 500.0,
                    float(saved_used["value"]) if saved_used else 0.0,
                    saved_package["value"] if saved_package else "Monthly 500 GB",
                ),
            )
        connection.execute(
            "INSERT INTO system_logs (category, message, operator, created_at) VALUES (?, ?, ?, datetime('now'))",
            ("ADMIN ACTION", f"Internet mode changed to {mode}", "System Operator"),
        )
