from quota.engine import calculate_quota_status


def test_block_threshold_keeps_actual_usage_and_exhausts_display():
    result = calculate_quota_status(50, 40, threshold_percentage=80)

    assert result.actual_used_gb == 40
    assert result.actual_usage_percentage == 80
    assert result.display_usage_percentage == 100
    assert result.remaining_gb == 10
    assert result.status == "BLOCKED"


def test_active_user_keeps_actual_display_percentage():
    result = calculate_quota_status(50, 21)

    assert result.actual_usage_percentage == 42
    assert result.display_usage_percentage == 42
    assert result.status == "ACTIVE"
