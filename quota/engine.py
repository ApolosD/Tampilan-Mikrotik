from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaStatus:
    quota_gb: float
    actual_used_gb: float
    actual_usage_percentage: float
    display_usage_percentage: float
    remaining_gb: float
    status: str
    blocked: bool


def calculate_quota_status(
    quota_gb: float,
    actual_used_gb: float,
    threshold_percentage: float = 80.0,
    blocked: bool = False,
) -> QuotaStatus:
    """Calculate quota values without mutating the actual usage value."""
    safe_quota = max(float(quota_gb), 0.0)
    actual_used = max(float(actual_used_gb), 0.0)
    actual_percentage = round((actual_used / safe_quota) * 100, 2) if safe_quota else 0.0
    should_block = blocked or (safe_quota > 0 and actual_percentage >= threshold_percentage)
    display_percentage = 100.0 if should_block else min(actual_percentage, 100.0)
    remaining = round(max(safe_quota - actual_used, 0.0), 2)

    if should_block:
        status = "BLOCKED"
    elif actual_percentage >= threshold_percentage:
        status = "WARNING"
    elif actual_percentage > 0:
        status = "ACTIVE"
    else:
        status = "UNUSED"

    return QuotaStatus(
        quota_gb=round(safe_quota, 2),
        actual_used_gb=round(actual_used, 2),
        actual_usage_percentage=actual_percentage,
        display_usage_percentage=display_percentage,
        remaining_gb=remaining,
        status=status,
        blocked=should_block,
    )
