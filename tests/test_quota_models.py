from quota.allocation import allocation_summary, equal_allocation
from quota.forecast import calculate_forecast


def test_equal_allocation_and_pool_summary():
    assert equal_allocation(500, 10) == 50
    assert allocation_summary(500, [100, 75, 50])["unallocated_gb"] == 275


def test_forecast_warns_when_exhaustion_precedes_period_end():
    forecast = calculate_forecast(327.4, 500, days_elapsed=20, days_remaining=11)

    assert forecast.average_daily_gb == 16.37
    assert forecast.days_until_exhaustion == 10.5
    assert forecast.warning is True