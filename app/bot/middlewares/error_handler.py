"""Middleware: глобальный перехват исключений."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger


class ErrorHandlerMiddleware(BaseMiddleware):
    """Ловит исключения, логирует и уведомляет пользователя."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            logger.exception(f"Unhandled error: {exc}")
            await self._notify(event)
            return None

    @staticmethod
    async def _notify(event: TelegramObject) -> None:
        text = "⚠️ Произошла ошибка. Попробуйте позже."
        try:
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
        except Exception:
            pass