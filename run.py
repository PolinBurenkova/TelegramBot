"""Entry point. Run: python run.py"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.bot_factory import create_bot, setup_bot_ui
from app.bot.dispatcher import create_dispatcher, ensure_no_polling_conflict
from app.config import Settings
from app.exceptions import PollingConflictError
from app.models.base import init_models
from app.utils.http_client import close_http_session
from app.utils.logger import setup_logging
from app.utils.single_instance import SingleInstance

log = logging.getLogger("bot")


def acquire_instance_lock(settings: Settings) -> SingleInstance | None:
    """Лок одного экземпляра: второй процесс с тем же токеном не запустится."""
    if not settings.bot.single_instance:
        return None
    lock = SingleInstance()
    if not lock.acquire():
        log.error(
            "Бот уже запущен на этой машине: лок %s занят. Остановите другой "
            "процесс run.py (PowerShell: Get-CimInstance Win32_Process | "
            "Where-Object CommandLine -match 'run\\.py') или задайте "
            "BOT_SINGLE_INSTANCE=false",
            lock.path,
        )
        raise SystemExit(1)
    return lock


async def shutdown(bot: Bot, dp: Dispatcher, lock: SingleInstance | None) -> None:
    """Закрыть сессию бота, storage и снять лок экземпляра.

    Вызывается из ``finally``, поэтому не должна падать: иначе при ошибке
    запуска (например, 401 Unauthorized) остаются незакрытые aiohttp-коннекторы,
    и интерпретатор шумит «Unclosed connector» / «Event loop is closed».
    """
    try:
        await close_http_session()
    except Exception:  # noqa: BLE001
        pass
    try:
        await dp.storage.close()
    except Exception:  # noqa: BLE001
        pass
    try:
        await bot.session.close()
    except Exception:  # noqa: BLE001
        pass
    if lock is not None:
        try:
            lock.release()
        except Exception:  # noqa: BLE001
            pass
    # Дать транспортам шанс завершиться до закрытия loop в asyncio.run().
    await asyncio.sleep(0)


async def main() -> None:
    settings = Settings()
    setup_logging(settings.logging)
    lock = acquire_instance_lock(settings)

    if settings.db_fallback_used:
        log.warning(
            "PostgreSQL недоступен (%s:%s) - включён dev-fallback на SQLite: %s. "
            "Для работы с Postgres: docker compose up -d postgres",
            settings.db_host,
            settings.db_port,
            settings.db_fallback_url,
        )

    # Ensure tables exist (idempotent; use Alembic in production)
    try:
        await init_models()
    except Exception as exc:
        from app.database import database_hint

        log.error(database_hint(exc))
        raise

    bot = create_bot(settings)
    dp = create_dispatcher(settings)

    try:
        # Единое меню команд и кнопка меню на всех платформах (мобильный/десктоп).
        # getMe() внутри заодно проверяет токен: при 401 сразу понятная ошибка.
        await setup_bot_ui(bot)
        log.info("Bot starting...")
        await ensure_no_polling_conflict(bot)
        await dp.start_polling(bot)
    finally:
        await shutdown(bot, dp, lock)


if __name__ == "__main__":
    from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except TelegramUnauthorizedError:
        log.error(
            "Telegram отклонил BOT_TOKEN (401). Причины: токен отозван (/revoke), "
            "взят от другого бота или с опечаткой. Проверьте в браузере "
            "https://api.telegram.org/bot<TOKEN>/getMe (должно быть ok:true и "
            "username нужного бота) и возьмите токен в @BotFather → /mybots → "
            "ваш бот → API Token, затем перезапустите."
        )
        raise SystemExit(1)
    except TelegramNetworkError as exc:
        log.error(
            "Нет связи с api.telegram.org (%s). Задайте BOT_PROXY в .env или "
            "проверьте интернет; офлайн-проверка: python -m scripts.healthcheck",
            exc,
        )
        raise SystemExit(1)
    except PollingConflictError as exc:
        log.error("%s", exc)
        raise SystemExit(1)
