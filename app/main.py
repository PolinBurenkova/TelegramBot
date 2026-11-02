"""Entry point for Cities Plus Bot.

Run:
    python -m app.main
or:
    python run.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from app.bot.bot_factory import setup_bot_ui
from app.config import get_settings
from app.exceptions import PollingConflictError
from app.models.base import init_models
from app.utils.single_instance import SingleInstance


# ---------- Logging ----------
def setup_logger(level: str = "INFO") -> None:
    """Configure loguru with console + rotating file handlers."""
    Path("logs").mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
            "<level>{level: <8}</level> "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> — <level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=False,
    )
    logger.add(
        "logs/bot.log",
        level=level,
        rotation="10 MB",
        retention=5,
        encoding="utf-8",
        enqueue=True,
    )
    logger.add(
        "logs/errors.log",
        level="ERROR",
        rotation="10 MB",
        retention=5,
        encoding="utf-8",
        backtrace=True,
        # diagnose=True печатает значения переменных из трейсбека — в них может
        # попасть токен бота и другие секреты, поэтому выключено.
        diagnose=False,
        enqueue=True,
    )
    logger.add(
        "logs/api.log",
        level="INFO",
        rotation="10 MB",
        retention=5,
        encoding="utf-8",
        filter=lambda record: "api" in record["name"],
        enqueue=True,
    )


# ---------- Bot / Dispatcher ----------
def create_bot() -> Bot:
    """Build Bot instance from settings (delegates to app.bot.bot_factory)."""
    settings = get_settings()
    if not settings.bot.token:
        logger.error("BOT_TOKEN is empty — set it in .env")
        sys.exit(1)
    from app.bot.bot_factory import create_bot as _factory_create_bot

    return _factory_create_bot(settings)


def create_dispatcher() -> Dispatcher:
    """Build Dispatcher (delegates to app.bot.dispatcher)."""
    from app.bot.dispatcher import create_dispatcher as _factory_create_dispatcher

    return _factory_create_dispatcher()


# ---------- Polling / Webhook ----------
def acquire_instance_lock() -> SingleInstance | None:
    """Занять лок одного экземпляра; при занятом локе — понятная ошибка.

    Второй процесс с тем же токеном забирает `getUpdates`, Telegram отвечает
    TelegramConflictError, а aiogram ретраит его бесконечно.
    """
    if not get_settings().bot.single_instance:
        return None
    lock = SingleInstance()
    if not lock.acquire():
        logger.error(
            "Бот уже запущен на этой машине: лок {} занят другим процессом. "
            "Остановите его (PowerShell: Get-CimInstance Win32_Process | "
            "Where-Object CommandLine -match 'run\\.py') или запустите с "
            "BOT_SINGLE_INSTANCE=false, если действительно нужен второй экземпляр.",
            lock.path,
        )
        sys.exit(1)
    logger.debug("Instance lock acquired: {}", lock.path)
    return lock


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    """Long-polling mode (default, works locally)."""
    from app.bot.dispatcher import ensure_no_polling_conflict

    logger.info("Starting polling...")
    await ensure_no_polling_conflict(bot)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    """Webhook mode (production)."""
    settings = get_settings()
    logger.info("Setting webhook: {}", settings.bot.webhook_url)
    await bot.set_webhook(
        settings.bot.webhook_url,
        secret_token=settings.bot.webhook_secret or None,
        drop_pending_updates=True,
    )
    await dp.start_webhook(
        bot,
        webhook_path="/webhook",
        secret_token=settings.bot.webhook_secret or None,
        host="0.0.0.0",
        port=8080,
    )


# ---------- Entry point ----------
async def main() -> None:
    """Configure and run the bot."""
    settings = get_settings()
    setup_logger(settings.logging.level)
    lock = acquire_instance_lock()

    logger.info("Cities Plus Bot v{} starting...", __import__("app").__version__)
    logger.info("Database: {}", settings.database.url)
    if settings.db_fallback_used:
        logger.warning(
            "PostgreSQL недоступен ({}:{}) — включён dev-fallback на SQLite: {}. "
            "Чтобы работать с Postgres, поднимите его (`docker compose up -d postgres`) "
            "или отключите fallback через DB_FALLBACK_SQLITE=false",
            settings.db_host,
            settings.db_port,
            settings.db_fallback_url,
        )
    logger.info("Default locale: {}", settings.default_locale)
    logger.info("Admins: {}", settings.admin.ids)
    logger.info("Production: {}", settings.is_production)

    # Ensure tables exist (idempotent; Alembic is preferred in production)
    try:
        Path("data").mkdir(parents=True, exist_ok=True)
        await init_models()
        logger.info("Database tables ensured")
    except Exception as exc:
        from app.database import database_hint

        logger.error(database_hint(exc))
        logger.exception("Failed to init database")
        raise

    bot = create_bot()
    dp = create_dispatcher()

    try:
        # Единое меню команд и кнопка меню на всех платформах (мобильный/десктоп).
        # getMe() внутри заодно проверяет токен: при 401 сразу понятная ошибка.
        await setup_bot_ui(bot)
        if settings.bot.use_webhook and settings.bot.webhook_url:
            await run_webhook(bot, dp)
        else:
            await run_polling(bot, dp)
    finally:
        try:
            await dp.storage.close()
        except Exception:
            pass
        try:
            await bot.session.close()
        except Exception:
            pass
        try:
            from app.utils.http_client import close_http_session

            await close_http_session()
        except Exception:
            pass
        if lock is not None:
            try:
                lock.release()
            except Exception:
                pass
        # Дать транспортам завершиться до закрытия loop в asyncio.run().
        await asyncio.sleep(0)
        logger.info("Bot stopped")


if __name__ == "__main__":
    from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except SystemExit:
        # Собственный выход (например, занятый лок экземпляра) уже залогирован.
        raise
    except TelegramUnauthorizedError:
        logger.error(
            "Telegram отклонил BOT_TOKEN (401 Unauthorized). Причины: токен "
            "отозван (/revoke), скопирован от другого бота или с опечаткой. "
            "Проверьте в браузере https://api.telegram.org/bot<TOKEN>/getMe — "
            "должно вернуться \"ok\":true и username нужного бота. Актуальный "
            "токен: @BotFather → /mybots → ваш бот → API Token. После правки "
            ".env перезапустите бота."
        )
        sys.exit(1)
    except PollingConflictError as exc:
        logger.error("{}", exc)
        sys.exit(1)
    except TelegramNetworkError as exc:
        settings = get_settings()
        logger.error(
            "Нет связи с api.telegram.org: {}. Это сетевая проблема, а не ошибка "
            "кода: бот уже прошёл инициализацию БД и диспетчера. Варианты без "
            "правки кода: (1) включить VPN на уровне ОС — тогда BOT_PROXY не "
            "нужен; (2) запустить бота на машине/сервере, где Telegram доступен "
            "(docker compose up -d); (3) задать BOT_PROXY в .env, если есть "
            "прокси, например http://host:port или socks5://host:1080 (для socks "
            "нужен пакет aiohttp_socks). Сейчас BOT_PROXY: {}. Офлайн-проверка "
            "без Telegram: python -m scripts.healthcheck",
            exc,
            settings.bot.proxy or "не задан",
        )
        sys.exit(1)
    except Exception as e:
        logger.exception("Fatal error: {}", e)
        sys.exit(1)