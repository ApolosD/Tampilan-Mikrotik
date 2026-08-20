def format_gb(value: float) -> str:
    return f"{float(value):,.1f} GB"


def format_currency(value: float) -> str:
    return f"Rp {float(value):,.0f}".replace(",", ".")
