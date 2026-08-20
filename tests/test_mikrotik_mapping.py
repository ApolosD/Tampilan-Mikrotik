from mikrotik import monitoring
from mikrotik.monitoring import normalize_hotspot_users


def test_hotspot_username_is_the_crew_identity():
    users = [
        {
            "name": "OS1",
            "profile": "profile-unlimited",
            "bytes-in": "1048576",
            "bytes-out": "2097152",
        }
    ]
    active = [
        {
            "user": "OS1",
            "address": "192.168.88.13",
            "mac-address": "AA:BB:CC:DD:EE:FF",
            "bytes-in": "1048576",
            "bytes-out": "4194304",
            "rx-rate": "1628",
            "tx-rate": "859",
        }
    ]

    result = normalize_hotspot_users(users, active)[0]

    assert result["username"] == "OS1"
    assert result["name"] == "OS1"
    assert result["ip_address"] == "192.168.88.13"
    assert result["mac_address"] == "AA:BB:CC:DD:EE:FF"
    assert result["is_online"] is True
    assert result["used_gb"] > 0


def test_default_trial_is_excluded_from_hotspot_users():
    users = [
        {"name": "default-trial", "profile": "default"},
        {"name": "DEFAULT-TRIAL", "profile": "default"},
        {"name": "OS1", "profile": "profile-unlimited"},
    ]

    result = normalize_hotspot_users(users, [])

    assert [item["username"] for item in result] == ["OS1"]


def test_ap_flow_accepts_space_alias_and_combines_rates():
    snapshot = {"interfaces": [{"name": "AP 01", "rx-rate": "1000000", "tx-rate": "2500000"}]}

    flow = monitoring.ap_interface_flow(snapshot, "AP-01")

    assert flow["name"] == "AP 01"
    assert monitoring.traffic_mbps(flow) == 3.5


def test_hotspot_activity_records_login_and_logout(monkeypatch):
    events = []
    monkeypatch.setattr(monitoring, "log_system_event", lambda category, message, operator: events.append((category, operator)))

    monitoring.record_hotspot_activity({"crew01"}, {"crew02"})

    assert events == [("HOTSPOT LOGIN", "crew02"), ("HOTSPOT LOGOUT", "crew01")]
