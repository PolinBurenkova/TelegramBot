"""Throttling middleware."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject

from app.bot.middlewares.base import BaseMiddleware, unwrap_event
from app.constants import THROTTLE_RATE


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = THROTTLE_RATE) -> None:
        self.rate = rate
        self._last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # На уровне dp.update приходит Update: для проверки пользователя и
        # ответа нужно вложенное событие, но дальше передаём исходный объект.
        inner = unwrap_event(event)
        tg_user = getattr(inner, "from_user", None)
        if tg_user is None:
            return await handler(event, data)
        uid = tg_user.id
        now = time.time()
        if now - self._last.get(uid, 0.0) < self.rate:
            if isinstance(inner, Message):
                await inner.answer("⏳ Слишком часто")
            elif isinstance(inner, CallbackQuery):
                await inner.answer("⏳ Слишком часто", show_alert=False)
            return None
        self._last[uid] = now
        return await handler(event, data)
