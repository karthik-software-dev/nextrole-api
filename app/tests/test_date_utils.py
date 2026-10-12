from datetime import date, datetime, timedelta, timezone
import pytest

from core.date_utils import resolve_date_range_dates, compute_comparative_date_windows


def test_resolve_date_range_dates_today():
    today = date.today()
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates("today")
    assert s_date == today
    assert e_date == today
    assert start_dt.year == today.year and start_dt.month == today.month and start_dt.day == today.day
    assert start_dt.hour == 0 and start_dt.minute == 0 and start_dt.second == 0
    assert end_dt.hour == 23 and end_dt.minute == 59 and end_dt.second == 59


def test_resolve_date_range_dates_yesterday():
    today = date.today()
    yesterday = today - timedelta(days=1)
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates("yesterday")
    assert s_date == yesterday
    assert e_date == yesterday
    assert start_dt.day == yesterday.day
    assert end_dt.day == yesterday.day


def test_resolve_date_range_dates_7d():
    today = date.today()
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates("7d")
    assert s_date == today - timedelta(days=6)
    assert e_date == today
    assert (e_date - s_date).days == 6


def test_resolve_date_range_dates_30d():
    today = date.today()
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates("30d")
    assert s_date == today - timedelta(days=29)
    assert e_date == today


def test_resolve_date_range_dates_month():
    today = date.today()
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates("month")
    assert s_date == today.replace(day=1)
    assert e_date == today


def test_resolve_date_range_dates_custom():
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates(
        "custom", start_date="2026-10-01", end_date="2026-10-05"
    )
    assert s_date == date(2026, 10, 1)
    assert e_date == date(2026, 10, 5)


def test_resolve_date_range_dates_custom_inverted():
    # If inverted, it should swap them gracefully
    s_date, e_date, start_dt, end_dt = resolve_date_range_dates(
        "custom", start_date="2026-10-10", end_date="2026-10-01"
    )
    assert s_date == date(2026, 10, 1)
    assert e_date == date(2026, 10, 10)


def test_compute_comparative_date_windows_today():
    curr_start, curr_end, prev_start, prev_end = compute_comparative_date_windows("today")
    assert curr_start.hour == 0 and curr_start.minute == 0
    assert prev_end == curr_start
    assert (curr_end - curr_start).total_seconds() >= 0


def test_compute_comparative_date_windows_yesterday():
    curr_start, curr_end, prev_start, prev_end = compute_comparative_date_windows("yesterday")
    assert curr_end.hour == 0 and curr_end.minute == 0
    assert (curr_end - curr_start) == timedelta(days=1)
    assert prev_end == curr_start


def test_compute_comparative_date_windows_7d():
    curr_start, curr_end, prev_start, prev_end = compute_comparative_date_windows("7d")
    assert (curr_end - curr_start) == timedelta(days=7)
    assert prev_end == curr_start
    assert (prev_end - prev_start) == timedelta(days=7)


def test_compute_comparative_date_windows_30d():
    curr_start, curr_end, prev_start, prev_end = compute_comparative_date_windows("30d")
    assert (curr_end - curr_start) == timedelta(days=30)
    assert prev_end == curr_start
    assert (prev_end - prev_start) == timedelta(days=30)
