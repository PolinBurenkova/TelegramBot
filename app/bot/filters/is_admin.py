"""Фильтр «администратор»."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.config import get_settings


class IsAdmin(BaseFilter):
    """Пропускает только пользователей из ADMIN_IDS."""

    async def __call__(self, event: TelegramObject) -> bool:  # type: ignore[override]
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return user.id in get_settings().admin_ids
