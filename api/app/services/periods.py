PERIODS = {"3m": 3, "6m": 6, "12m": 12, "all": 0}


def resolve(available: list[str], period: str | None = "all", start: str | None = None, end: str | None = None) -> list[str]:
    months = sorted(set(available))
    if start or end:
        return [m for m in months if (not start or m >= start) and (not end or m <= end)]
    n = PERIODS.get(period or "all", 0)
    return months[-n:] if n else months
