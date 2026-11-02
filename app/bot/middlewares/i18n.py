"""Middleware: локализация (определяет язык пользователя, кладёт переводчик)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import TelegramObject

from app.bot.middlewares.base import BaseMiddleware, unwrap_event
from app.config import settings
from app.utils.i18n import DEFAULT_LOCALE, Translator, translator

SUPPORTED: frozenset[str] = frozenset({"ru", "en"})


def _locale_from(user: Any) -> str:
    """Локаль пользователя: профиль → language_code Telegram → дефолт."""
    explicit = getattr(user, "locale", None)
    if isinstance(explicit, str) and explicit in SUPPORTED:
        return explicit
    code = getattr(user, "language_code", None) or getattr(
        getattr(user, "from_user", None), "language_code", None
    )
    if isinstance(code, str) and code[:2].lower() in SUPPORTED:
        return code[:2].lower()
    return getattr(settings, "default_locale", DEFAULT_LOCALE) or DEFAULT_LOCALE


class I18nMiddleware(BaseMiddleware):
    """Кладёт ``locale``, ``tr`` и совместимый ``lang`` в data хендлера."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # data["user"] уже выставлен UserContextMiddleware; запасной путь —
        # from_user из вложенного события (на dp.update приходит Update).
        user = data.get("user") or getattr(unwrap_event(event), "from_user", None)
        locale = _locale_from(user)
        data["locale"] = locale
        data["lang"] = locale  # совместимость с прежним именем
        # UserContextMiddleware уже кладёт переводчик по локали из профиля:
        # не перетираем его, если он есть.
        data.setdefault("tr", translator(locale))
        data.setdefault("_", data["tr"].t)
        return await handler(event, data)


__all__ = ["I18nMiddleware", "Translator", "SUPPORTED"]
