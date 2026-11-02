"""Create Dispatcher with middlewares, routers and lifecycle hooks."""
from __future__ import annotations

import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.fsm.strategy import FSMStrategy

from app.bot.middlewares.db_session import DbSessionMiddleware
from app.bot.middlewares.i18n import I18nMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.bot.middlewares.metrics import MetricsMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.bot.middlewares.user_context import UserContextMiddleware
from app.bot.storage import create_storage
from app.config import Settings, get_settings
from app.exceptions import PollingConflictError
from app.handlers import root_router
from app.services.external.registry import ExternalRegistry
from app.utils.http_client import close_http_session, create_http_session

log = logging.getLogger("bot")


def create_dispatcher(settings: Settings | None = None) -> Dispatcher:
    """Build Dispatcher. Uses get_settings() if not provided."""
    if settings is None:
        settings = get_settings()

    dp = Dispatcher(
        storage=create_storage(settings),
        fsm_strategy=FSMStrategy.USER_IN_CHAT,
    )

    # Middlewares — order matters
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(MetricsMiddleware())
    dp.update.outer_middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(UserContextMiddleware())
    # I18n идёт последним: ему нужен data["user"] из UserContextMiddleware,
    # переводчик из профиля он не перетирает (setdefault).
    dp.update.outer_middleware(I18nMiddleware())

    dp.include_router(root_router)

    @dp.startup()
    async def _on_startup() -> None:
        session: httpx.AsyncClient = create_http_session()
        dp["http_session"] = session
        dp["external"] = ExternalRegistry(session)
        log.info("Startup complete")

    @dp.shutdown()
    async def _on_shutdown() -> None:
        await close_http_session()
        log.info("Shutdown complete")

    return dp


async def ensure_no_polling_conflict(bot: Bot) -> None:
    """Проверить, что обновления не забирает другой экземпляр бота.

    aiogram внутри `_polling` бесконечно ретраит `TelegramConflictError`, из-за
    чего в логе копится бесконечная серия `Failed to fetch updates`, а бот не
    работает. Поэтому делаем один короткий `getUpdates` заранее: если токен уже
    кем-то используется (второй `run.py`, контейнер, бот на сервере или активный
    webhook), получаем понятную ошибку сразу.

    Проверка не расходует обновления: без `offset` они не подтверждаются.
    """
    from aiogram.exceptions import TelegramConflictError

    try:
        await bot.get_updates(limit=1, timeout=0)
    except TelegramConflictError as exc:
        raise PollingConflictError(
            "Обновления бота уже забирает другой экземпляр (getUpdates conflict). "
            "Остановите его: второй run.py в этой папке "
            "(PowerShell: Get-CimInstance Win32_Process | "
            "Where-Object CommandLine -match 'run\\.py'), контейнер "
            "`docker compose ps`, либо бот, запущенный на сервере. "
            "Либо у токена активен webhook — проверьте "
            "https://api.telegram.org/bot<TOKEN>/getWebhookInfo и сбросьте его "
            "через /webhook или bot.delete_webhook()."
        ) from exc