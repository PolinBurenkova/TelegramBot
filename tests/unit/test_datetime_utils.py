# tests/unit/test_datetime_utils.py
"""Юнит-тесты datetime-хелперов (`app/utils/datetime_utils.py`).

`time.sleep` не используется: humanize_delta проверяется на смещениях
относительно `utcnow()`, а не на ожидании.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.utils.datetime_utils import date_key, humanize_delta, to_user_tz, utcnow


def test_utcnow_is_timezone_aware_utc() -> None:
    now = utcnow()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_to_user_tz_converts_utc_to_moscow() -> None:
    dt = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)

    converted = to_user_tz(dt, "Europe/Moscow")

    assert converted.hour == 12
    assert converted.tzinfo is not None
    assert converted.utcoffset() == timedelta(hours=3)


def test_to_user_tz_treats_naive_datetime_as_utc() -> None:
    dt = datetime(2026, 1, 15, 9, 0)

    converted = to_user_tz(dt, "Europe/Moscow")

    assert converted.hour == 12
    assert converted.utcoffset() == timedelta(hours=3)


def test_to_user_tz_unknown_zone_returns_input() -> None:
    dt = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)

    assert to_user_tz(dt, "Not/AZone") == dt


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (timedelta(seconds=0), "только что"),
        (timedelta(seconds=59), "только что"),
        (timedelta(minutes=1), "1 минуту назад"),
        (timedelta(minutes=5), "5 минут назад"),
        (timedelta(minutes=21), "21 минуту назад"),
        (timedelta(hours=2), "2 часа назад"),
        (timedelta(hours=5), "5 часов назад"),
        (timedelta(hours=24), "1 день назад"),
        (timedelta(days=3), "3 дня назад"),
        (timedelta(days=11), "11 дней назад"),
    ],
    ids=[
        "now",
        "59s",
        "1min",
        "5min",
        "21min",
        "2h",
        "5h",
        "1day",
        "3days",
        "11days",
    ],
)
def test_humanize_delta(delta: timedelta, expected: str) -> None:
    assert humanize_delta(utcnow() - delta) == expected


def test_date_key_from_explicit_date() -> None:
    assert date_key(date(2026, 3, 9)) == "2026-03-09"


def test_date_key_defaults_to_today() -> None:
    assert date_key() == date.today().isoformat()
