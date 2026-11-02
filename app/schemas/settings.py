"""Settings schemas."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class SettingsSchema(BaseSchema):
    """User settings view."""

    locale: str = "ru"
    notify: bool = True
    difficulty: str = "easy"
    timezone: str = "UTC"


class SettingsUpdate(BaseSchema):
    """Partial settings update."""

    locale: str | None = None
    notify: bool | None = None
    difficulty: str | None = None
    timezone: str | None = None