"""Shared market-evidence quality checks."""


LIMITED_DAILY_CHANGE_QUALITIES = {"limited", "unavailable"}


def has_reliable_daily_change(data):
    """Return whether a record can support daily-movement conclusions."""
    if not data or data.get("percent_change") is None:
        return False
    quality = str(data.get("daily_change_quality") or "").strip().lower()
    return quality not in LIMITED_DAILY_CHANGE_QUALITIES
