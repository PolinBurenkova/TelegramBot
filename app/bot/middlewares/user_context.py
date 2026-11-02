"""User context middleware."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import TelegramObject

from app.bot.middlewares.base import BaseMiddleware, event_user
from app.services.user_service import UserService
from app.utils.i18n import translator


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if session is None:
            return await handler(event, data)

        # На dp.update.outer_middleware приходит Update — разворачиваем в Message
        # или CallbackQuery, иначе from_user всегда None.
        tg_user = event_user(event)
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        svc = UserService(session)
        user = await svc.get_or_create(tg_user.id, tg_user.username)
        data["user"] = user
        data["profile"] = user.profile
        data["_"] = translator(user.locale).t
        # Вниз передаём исходное событие (Update), иначе сломается роутинг.
        return await handler(event, data)
