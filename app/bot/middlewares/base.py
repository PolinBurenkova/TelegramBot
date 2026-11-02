"""Базовый middleware и хелперы для update-level событий."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

#: Поля ``Update``, в которых лежит реальное событие.
_UPDATE_EVENT_FIELDS = (
    "message",
    "edited_message",
    "channel_post",
    "edited_channel_post",
    "business_message",
    "edited_business_message",
    "callback_query",
    "inline_query",
    "shipping_query",
    "pre_checkout_query",
    "poll",
    "poll_answer",
    "my_chat_member",
    "chat_member",
    "chat_join_request",
)


def unwrap_event(event: TelegramObject) -> TelegramObject:
    """Вернуть вложенное событие, если пришёл ``Update``.

    Middleware, зарегистрированные через ``dp.update.outer_middleware``,
    получают именно ``Update``, а не ``Message``/``CallbackQuery``. Без
    разворачивания ``event.from_user`` всегда ``None``, и, например,
    ``UserContextMiddleware`` молча не кладёт ``user`` в ``data`` — тогда
    хендлеры с параметром ``user`` падают с TypeError.
    """
    if isinstance(event, Update):
        for name in _UPDATE_EVENT_FIELDS:
            inner = getattr(event, name, None)
            if inner is not None:
                return inner
    return event


def event_user(event: TelegramObject) -> Any | None:
    """Пользователь события (``from_user``) с учётом ``Update``."""
    return getattr(unwrap_event(event), "from_user", None)


class BaseBotMiddleware(BaseMiddleware):
    """Промежуточный класс для middleware."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        return await handler(event, data)


# Обратная совместимость: db_session/logging/throttling/user_context импортируют
# это имя именно из app.bot.middlewares.base.
BaseMiddleware = BaseBotMiddleware

__all__ = ["BaseBotMiddleware", "BaseMiddleware", "event_user", "unwrap_event"]
