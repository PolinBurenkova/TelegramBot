"""Схемы пользователей."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class UserCreate(BaseSchema):
    """Создание пользователя."""

    telegram_id: int
    username: str | None = None


class UserOut(BaseSchema):
    """Пользователь наружу."""

    id: int
    telegram_id: int
    username: str | None = None
    locale: str = "ru"
    level: int = 0
