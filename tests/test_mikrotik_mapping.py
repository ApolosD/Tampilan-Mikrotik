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
    snapshot = {"interfaces": [{"name": "AP 1", "rx-rate": "1000000", "tx-rate": "2500000"}]}

    flow = monitoring.ap_interface_flow(snapshot, "AP-01")

    assert flow["name"] == "AP 1"
    assert monitoring.traffic_mbps(flow) == 3.5


def test_traffic_uses_counter_delta_when_live_rate_is_zero():
    previous = {"rx_bytes": 1_000_000, "tx_bytes": 2_000_000}
    current = {"rx_bytes": 2_000_000, "tx_bytes": 4_000_000, "rx_rate": "0", "tx_rate": "0"}

    assert monitoring.traffic_mbps(current, previous, 2) == 12.0


def test_hotspot_activity_records_login_and_logout(monkeypatch):
    events = []
    monkeypatch.setattr(monitoring, "log_system_event", lambda category, message, operator: events.append((category, operator)))

    monitoring.record_hotspot_activity({"crew01"}, {"crew02"})

    assert events == [("HOTSPOT LOGIN", "crew02"), ("HOTSPOT LOGOUT", "crew01")]


def test_ap_port_mapping_resolves_from_ether_ports():
    snapshot = {
        "interfaces": [
            {"name": "ether2", "running": "true", "disabled": "false", "rx-byte": "100", "tx-byte": "200", "rx-rate": "0", "tx-rate": "0"},
            {"name": "ether3", "running": "true", "disabled": "false", "rx-byte": "100", "tx-byte": "200", "rx-rate": "0", "tx-rate": "0"},
            {"name": "ether4", "running": "false", "disabled": "false", "rx-byte": "100", "tx-byte": "200", "rx-rate": "0", "tx-rate": "0"},
        ]
    }

    mapped = monitoring.mapped_ap_port_flows(snapshot)

    assert [item["label"] for item in mapped] == ["AP 1", "AP 2", "AP 3"]
    assert [item["resolved_interface"] for item in mapped] == ["ether2", "ether3", "ether4"]
    assert mapped[0]["flow"]["running"] is True
    assert mapped[2]["flow"]["running"] is False


def test_starlink_upstream_uses_ether1_alias():
    snapshot = {"interfaces": [{"name": "ether1", "running": "true", "disabled": "false", "rx-byte": "1", "tx-byte": "2", "rx-rate": "0", "tx-rate": "0"}]}

    upstream = monitoring.starlink_interface_flow(snapshot)

    assert upstream is not None
    assert upstream["name"] == "ether1"
