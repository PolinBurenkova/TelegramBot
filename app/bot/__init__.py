"""Сборка бота и диспетчера.

Импорты ленивые (PEP 562): app.bot.dispatcher тянет за собой все хендлеры,
а хендлер admin импортирует фильтры из app.bot — прямой импорт создаёт
цикл. __getattr__ разрывает его.
"""
from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "create_bot":
        from app.bot.bot_factory import create_bot

        return create_bot
    if name == "create_dispatcher":
        from app.bot.dispatcher import create_dispatcher

        return create_dispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_bot", "create_dispatcher"]
