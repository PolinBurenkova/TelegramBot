"""Create configured Bot instance and register the command menu."""
from __future__ import annotations

import importlib.util

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand, MenuButtonCommands
from loguru import logger

from app.config import Settings

#: Команды бота: единый список для мобильного и десктопного клиента.
#: Показываются в меню «/» и за кнопкой меню у поля ввода.
BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "🏙 Главное меню"),
    ("menu", "📋 Показать меню"),
    ("play", "🎮 Играть в «Города»"),
    ("geo", "🌍 GeoGuessr — угадать город"),
    ("profile", "👤 Профиль и статистика"),
    ("achievements", "🏆 Достижения"),
    ("leaderboard", "📊 Топ игроков"),
    ("settings", "⚙️ Настройки"),
    ("help", "❓ Справка"),
    ("cancel", "↩️ Отменить и вернуться в меню"),
)

SHORT_DESCRIPTION = "Города и GeoGuessr: цепочка городов, очки, достижения и рейтинг."
DESCRIPTION = (
    "«Города+» — классическая цепочка городов против бота и режим GeoGuessr.\n\n"
    "Нажмите /start или выберите пункт меню. Команды: /play, /geo, /profile, "
    "/achievements, /leaderboard, /settings, /help."
)


def create_session(settings: Settings) -> BaseSession:
    """Сессия Telegram: прокси и таймаут из настроек.

    Прокси нужен там, где ``api.telegram.org`` недоступен напрямую, — иначе
    ``bot.get_me()`` падает с ``TelegramNetworkError: Request timeout error``.
    Поддерживаются http/https и socks4/socks5 (для socks требуется
    необязательный пакет ``aiohttp_socks``).
    """
    # AiohttpSession → BaseSession принимает timeout как float (секунды),
    # а не ClientTimeout: см. aiogram/client/session/base.py::BaseSession.
    timeout = float(settings.bot.request_timeout)
    proxy = settings.bot.proxy
    if proxy:
        if proxy.startswith(("socks4://", "socks5://", "socks4h://", "socks5h://")):
            if importlib.util.find_spec("aiohttp_socks") is None:
                raise RuntimeError(
                    "Для socks-прокси нужен пакет aiohttp_socks: "
                    "pip install aiohttp_socks (или укажите http://-прокси в BOT_PROXY)"
                )
        return AiohttpSession(proxy=proxy, timeout=timeout)
    return AiohttpSession(timeout=timeout)


def create_bot(settings: Settings | None = None) -> Bot:
    """Build Bot. Uses get_settings() if not provided."""
    if settings is None:
        settings = Settings()
    return Bot(
        token=settings.bot.token,
        session=create_session(settings),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def setup_bot_ui(bot: Bot) -> None:
    """Зарегистрировать меню команд, кнопку меню и описание бота.

    Без ``set_my_commands`` мобильный и десктопный клиенты показывают разное:
    на телефоне у поля ввода нет списка команд, а на компьютере он может
    отсутствовать вовсе. Регистрация через Bot API выравнивает обе платформы:
    одинаковый список «/…», одинаковая кнопка меню и одинаковое приветствие в
    пустом чате. Ошибки сети не фатальны — бот продолжает работать.
    """
    # Проверяем токен и печатаем, какому боту он принадлежит: при опечатке или
    # токене от другого бота Telegram ответит 401 — так сразу видно причину.
    me = await bot.get_me()
    logger.info("Telegram: @{} (id={})", me.username or "без_username", me.id)

    try:
        await bot.set_my_commands(
            [BotCommand(command=name, description=text) for name, text in BOT_COMMANDS]
        )
        # Кнопка меню = список команд (а не web-app/пусто), как на мобильном,
        # так и на десктопе.
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except TelegramUnauthorizedError:
        raise  # неверный токен: пусть main покажет понятное сообщение
    except Exception as exc:  # noqa: BLE001 — оформление не должно ронять запуск
        logger.warning("Не удалось зарегистрировать меню команд: {}", exc)

    try:
        await bot.set_my_short_description(short_description=SHORT_DESCRIPTION)
        await bot.set_my_description(description=DESCRIPTION)
    except TelegramUnauthorizedError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось обновить описание бота: {}", exc)
