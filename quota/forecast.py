from dataclasses import dataclass


@dataclass(frozen=True)
class Forecast:
    average_daily_gb: float
    days_until_exhaustion: float | None
    projected_period_usage_gb: float
    warning: bool


def calculate_forecast(used_gb: float, total_quota_gb: float, days_elapsed: int, days_remaining: int) -> Forecast:
    average = round(max(used_gb, 0.0) / max(days_elapsed, 1), 2)
    remaining = max(total_quota_gb - used_gb, 0.0)
    days_to_exhaustion = round(remaining / average, 1) if average > 0 else None
    projected = round(average * max(days_remaining, 0), 2)
    return Forecast(
        average_daily_gb=average,
        days_until_exhaustion=days_to_exhaustion,
        projected_period_usage_gb=projected,
        warning=days_to_exhaustion is not None and days_to_exhaustion < days_remaining,
    )
