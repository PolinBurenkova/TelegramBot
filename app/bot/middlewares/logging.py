"""Logging middleware."""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import TelegramObject

from app.bot.middlewares.base import BaseMiddleware

log = logging.getLogger("handlers")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        t0 = time.perf_counter()
        tg_user = getattr(event, "from_user", None)
        uid = tg_user.id if tg_user else "-"
        result = await handler(event, data)
        dt = (time.perf_counter() - t0) * 1000
        # aiogram передаёт сюда не только функции, но и functools.partial
        # (цепочка middleware/FSM), поэтому __name__ может отсутствовать.
        handler_name = getattr(handler, "__name__", None) or type(handler).__name__
        log.info(
            "event=%s user=%s handler=%s ms=%.1f",
            type(event).__name__,
            uid,
            handler_name,
            dt,
        )
        return result