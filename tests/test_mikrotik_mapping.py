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
