from database.auth import hash_password, verify_password
from mikrotik import actions


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


def test_delete_hotspot_user_removes_user(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(actions, "open_connection", lambda: FakeConnection(api))

    removed = actions.delete_hotspot_user("crew01")

    assert removed is True
    assert api.paths[("ip", "hotspot", "user")].removed == ["*2"]
