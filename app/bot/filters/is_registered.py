"""Registered filter."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class IsRegistered(BaseFilter):
    async def __call__(self, event: TelegramObject, user: object = None) -> bool:
        return user is not None