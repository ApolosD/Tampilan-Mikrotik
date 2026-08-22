def equal_allocation(total_quota_gb: float, crew_count: int) -> float:
    if crew_count <= 0:
        return 0.0
    return round(max(total_quota_gb, 0.0) / crew_count, 2)


def allocation_summary(total_quota_gb: float, allocations: list[float]) -> dict[str, float]:
    allocated = round(sum(max(value, 0.0) for value in allocations), 2)
    return {
        "total_quota_gb": round(max(total_quota_gb, 0.0), 2),
        "allocated_gb": allocated,
        "unallocated_gb": round(max(total_quota_gb - allocated, 0.0), 2),
        "over_allocated_gb": round(max(allocated - total_quota_gb, 0.0), 2),
    }
