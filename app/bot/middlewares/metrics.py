"""Middleware: метрики обновлений (счётчики и время обработки в памяти)."""
from __future__ import annotations

import time
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import TelegramObject
from loguru import logger

from app.bot.middlewares.base import BaseMiddleware
from app.utils.metrics import inc

_events: Counter[str] = Counter()
_errors: Counter[str] = Counter()


def snapshot() -> dict[str, Any]:
    """Текущие счётчики (для healthcheck/админки)."""
    return {"events": dict(_events), "errors": dict(_errors)}


class MetricsMiddleware(BaseMiddleware):
    """Считает события по типу и логирует длительность обработки."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        kind = type(event).__name__
        _events[kind] += 1
        inc(f"update.{kind}")
        started = time.perf_counter()
        try:
            return await handler(event, data)
        except Exception:
            _errors[kind] += 1
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.debug("metrics: {} за {:.1f} мс", kind, elapsed_ms)


__all__ = ["MetricsMiddleware", "snapshot"]
