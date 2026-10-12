from datetime import date, datetime, time, timedelta, timezone


def resolve_date_range_dates(
    date_range: str = "7d",
    start_date: str | None = None,
    end_date: str | None = None,
    default_days: int = 7,
) -> tuple[date, date, datetime, datetime]:
    """Resolves standard date range presets into start/end date objects and inclusive UTC datetimes.

    Supported presets:
        - "today": current calendar date [00:00:00 -> 23:59:59.999999]
        - "yesterday": previous calendar date [00:00:00 -> 23:59:59.999999]
        - "7d": past 7 calendar days inclusive
        - "30d": past 30 calendar days inclusive
        - "month": 1st of current month through today
        - "custom": ISO formatted start_date and end_date
    """
    today = date.today()

    if date_range == "custom" and start_date and end_date:
        try:
            s_date = date.fromisoformat(start_date)
            e_date = date.fromisoformat(end_date)
        except Exception:
            s_date = today - timedelta(days=default_days - 1)
            e_date = today
        if s_date > e_date:
            s_date, e_date = e_date, s_date
    elif date_range == "today":
        s_date = today
        e_date = today
    elif date_range == "yesterday":
        s_date = today - timedelta(days=1)
        e_date = s_date
    elif date_range == "30d":
        s_date = today - timedelta(days=29)
        e_date = today
    elif date_range == "month":
        s_date = today.replace(day=1)
        e_date = today
    else:  # default (e.g. "7d")
        s_date = today - timedelta(days=default_days - 1)
        e_date = today

    start_dt = datetime.combine(s_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(e_date, time.max, tzinfo=timezone.utc)

    return s_date, e_date, start_dt, end_dt


def compute_comparative_date_windows(
    range_val: str = "30d",
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[datetime, datetime, datetime, datetime]:
    """Calculates current period [curr_start, curr_end] and preceding comparison period [prev_start, prev_end].

    Used by analytics services for KPI delta calculations and period-over-period comparisons.
    """
    now = datetime.now(timezone.utc)

    if range_val == "today":
        curr_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        curr_end = now
        prev_end = curr_start
        prev_start = prev_end - timedelta(days=1)
    elif range_val == "yesterday":
        curr_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        curr_start = curr_end - timedelta(days=1)
        prev_end = curr_start
        prev_start = prev_end - timedelta(days=1)
    elif range_val == "7d":
        curr_start = now - timedelta(days=7)
        curr_end = now
        prev_end = curr_start
        prev_start = curr_start - timedelta(days=7)
    elif range_val == "month":
        curr_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        curr_end = now
        duration = curr_end - curr_start
        prev_end = curr_start
        prev_start = curr_start - duration
    elif range_val == "custom" and start_date and end_date:
        try:
            curr_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            curr_end = datetime.fromisoformat(end_date).replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            duration = curr_end - curr_start
            prev_end = curr_start
            prev_start = curr_start - duration
        except Exception:
            curr_start = now - timedelta(days=30)
            curr_end = now
            prev_end = curr_start
            prev_start = curr_start - timedelta(days=30)
    else:  # Default "30d"
        curr_start = now - timedelta(days=30)
        curr_end = now
        prev_end = curr_start
        prev_start = curr_start - timedelta(days=30)

    return curr_start, curr_end, prev_start, prev_end
