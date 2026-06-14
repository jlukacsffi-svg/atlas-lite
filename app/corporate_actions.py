"""Corporate-action normalization for Atlas historical comparisons."""

from datetime import datetime, timezone


def normalize_prior_price(prior_price, prior_generated_at, current_data):
    """Return a split-adjusted prior price and the applied split events."""
    if prior_price in (None, 0) or not prior_generated_at:
        return prior_price, []

    prior_time = _parse_datetime(prior_generated_at)
    if prior_time is None:
        return prior_price, []

    splits = (current_data.get("momentum_metrics") or {}).get("recent_splits") or []
    applied = []
    cumulative_ratio = 1.0
    for split in splits:
        split_time = _parse_datetime(split.get("date"))
        ratio = _positive_float(split.get("ratio"))
        if split_time is None or ratio is None or split_time <= prior_time:
            continue
        cumulative_ratio *= ratio
        applied.append(split)

    if not applied:
        return prior_price, []
    return float(prior_price) / cumulative_ratio, applied


def describe_splits(ticker, splits):
    """Build a concise, auditable description of applied split events."""
    descriptions = []
    for split in splits:
        date = _parse_datetime(split.get("date"))
        date_text = date.date().isoformat() if date else "unknown date"
        descriptions.append(
            f"{ticker} {split.get('split_ratio', split.get('ratio'))} on {date_text}"
        )
    return descriptions


def _parse_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _positive_float(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
