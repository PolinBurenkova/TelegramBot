"""Datetime helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone


def utcnow() -> datetime:
    """UTC now (timezone-aware)."""
    return datetime.now(timezone.utc)


def to_user_tz(dt: datetime, tz: str) -> datetime:
    """Convert UTC datetime to user timezone via zoneinfo."""
    from zoneinfo import ZoneInfo
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(ZoneInfo(tz))
    except Exception:
        return dt


def humanize_delta(dt: datetime) -> str:
    """'5 минут назад' style."""
    from app.utils.text import pluralize
    delta = utcnow() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "только что"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} {pluralize(minutes, ('минуту', 'минуты', 'минут'))} назад"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} {pluralize(hours, ('час', 'часа', 'часов'))} назад"
    days = hours // 24
    return f"{days} {pluralize(days, ('день', 'дня', 'дней'))} назад"


def date_key(d: date | None = None) -> str:
    """YYYY-MM-DD."""
    return (d or date.today()).isoformat()