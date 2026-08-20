import sqlite3

from database import database
from database.auth import hash_password, verify_password
from mikrotik import actions
from mikrotik.monitoring import sync_hotspot_users


class FakePath(list):
    def __init__(self, values):
        super().__init__(values)
        self.removed = []
        self.updated = []
        self.added = []

    def remove(self, item_id):
        self.removed.append(item_id)

    def set(self, item_id, **values):
        self.updated.append((item_id, values))

    def add(self, **values):
        self.added.append(values)


class FakeApi:
    def __init__(self):
        self.paths = {
            ("ip", "hotspot", "active"): FakePath([{ ".id": "*1", "user": "crew01" }]),
            ("ip", "hotspot", "user"): FakePath([{ ".id": "*2", "name": "crew01" }]),
        }

    def path(self, *parts):
        return self.paths[parts]


class FakeConnection:
    def __init__(self, api):
        self.api = api

    def __enter__(self):
        return self.api

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_password_hash_is_not_plaintext_and_verifies():
    encoded = hash_password("admin1")

    assert encoded != "admin1"
    assert verify_password("admin1", encoded)
    assert not verify_password("wrong-password", encoded)


def test_kick_removes_matching_active_session(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(actions, "open_connection", lambda: FakeConnection(api))

    assert actions.kick_user("crew01") == 1
    assert api.paths[("ip", "hotspot", "active")].removed == ["*1"]


def test_block_updates_matching_hotspot_user(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(actions, "open_connection", lambda: FakeConnection(api))

    actions.set_user_blocked("crew01", True)

    assert api.paths[("ip", "hotspot", "user")].updated == [("*2", {"disabled": "yes"})]


def test_create_hotspot_user_adds_new_routeros_user(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(actions, "open_connection", lambda: FakeConnection(api))

    actions.create_hotspot_user("new-user", "pass1234", profile="default", shared_users=2)

    assert api.paths[("ip", "hotspot", "user")].added == [{"name": "new-user", "password": "pass1234", "profile": "default", "shared-users": "2"}]


def test_edit_hotspot_user_updates_existing_routeros_user(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(actions, "open_connection", lambda: FakeConnection(api))

    actions.edit_hotspot_user(
        "crew01",
        password="newpass123",
        profile="vip",
        shared_users=4,
        limit_uptime="7d",
        comment="updated profile",
    )

    assert api.paths[("ip", "hotspot", "user")].updated == [
        ("*2", {"password": "newpass123", "profile": "vip", "shared-users": "4", "limit-uptime": "7d", "comment": "updated profile"})
    ]


def test_sync_hotspot_users_updates_local_profile_and_limit_fields(monkeypatch, tmp_path):
    db_path = tmp_path / "mikrotik_dashboard.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.initialize_database()

    sync_hotspot_users({
        "connection": {"status": "ONLINE"},
        "active_users": [{"user": "crew01", "address": "10.0.0.2", "bytes-in": 100, "bytes-out": 100}],
        "users": [{"name": "crew01", "profile": "vip", "limit-uptime": "7d", "address": "10.0.0.2", "mac-address": "AA:BB:CC:DD:EE:FF"}],
    })

    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT profile, limit_uptime FROM crew WHERE username = ?", ("crew01",)).fetchone()

    assert row == ("vip", "7d")


def test_delete_hotspot_user_removes_user(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(actions, "open_connection", lambda: FakeConnection(api))

    removed = actions.delete_hotspot_user("crew01")

    assert removed is True
    assert api.paths[("ip", "hotspot", "user")].removed == ["*2"]
