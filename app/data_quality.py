"""Shared market-evidence quality checks."""


LIMITED_DAILY_CHANGE_QUALITIES = {"limited", "unavailable"}


def has_reliable_daily_change(data):
    """Return whether a record can support daily-movement conclusions."""
    if not data or data.get("percent_change") is None:
        return False
    quality = str(data.get("daily_change_quality") or "").strip().lower()
    return quality not in LIMITED_DAILY_CHANGE_QUALITIES


def daily_movement_summary(records):
    """Summarize whether a market snapshot can support entry decisions."""
    available = [
        data
        for data in (records or {}).values()
        if data and data.get("status") == "available"
    ]
    explicit_limited = sum(
        1
        for data in available
        if not has_reliable_daily_change(data)
    )
    nonzero_moves = sum(
        1
        for data in available
        if abs(float(data.get("percent_change") or 0)) > 0.0001
    )
    suspicious_all_zero = len(available) >= 5 and nonzero_moves == 0
    limited = bool(explicit_limited or suspicious_all_zero)
    if suspicious_all_zero:
        detail = (
            "The latest snapshot has prices but no usable daily movement. "
            "New paper entries are paused until a valid refresh."
        )
    elif explicit_limited:
        detail = (
            f"{explicit_limited} securities do not have a valid prior-close "
            "comparison. New paper entries are paused."
        )
    else:
        detail = (
            "Daily movement uses valid prior-close comparisons for the "
            "available securities."
        )
    return {
        "status": "limited" if limited else "complete",
        "limited": len(available) if suspicious_all_zero else explicit_limited,
        "suspicious_all_zero": suspicious_all_zero,
        "detail": detail,
    }
