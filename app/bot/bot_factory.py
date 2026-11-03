"""Create configured Bot instance and register the command menu."""
from __future__ import annotations

import importlib.util
import socket
from urllib.parse import urlsplit

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand, MenuButtonCommands
from loguru import logger

from app.config import Settings
from app.exceptions import ProxyUnavailableError

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


_PROXY_DEFAULT_PORTS: dict[str, int] = {
    "http": 8080,
    "https": 8080,
    "socks4": 1080,
    "socks4h": 1080,
    "socks5": 1080,
    "socks5h": 1080,
}


def proxy_endpoint(proxy: str) -> tuple[str, int]:
    """Вернуть (host, port) из строки прокси."""
    parts = urlsplit(proxy if "://" in proxy else f"http://{proxy}")
    port = parts.port or _PROXY_DEFAULT_PORTS.get(parts.scheme.lower(), 1080)
    return parts.hostname or "", port


def check_proxy_available(proxy: str, timeout: float = 2.0) -> None:
    """Проверить, что прокси из ``BOT_PROXY`` слушает свой порт.

    Прокси-клиент (v2rayN/xray и подобные) часто не запущен, и тогда
    ``aiohttp_socks`` падает с ``ProxyConnectionError`` и длинным трейсбеком.
    Проверяем заранее, чтобы выдать одну понятную ошибку с подсказкой.
    """
    host, port = proxy_endpoint(proxy)
    if not host:
        raise ProxyUnavailableError(
            f"Некорректный BOT_PROXY={proxy!r}: не удалось выделить хост и порт. "
            "Формат: http://host:port или socks5://host:port."
        )
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        raise ProxyUnavailableError(
            f"Прокси из BOT_PROXY недоступен ({host}:{port}): {exc}. "
            "Запустите прокси/VPN-клиент на этом порту либо уберите прокси: "
            "в PowerShell — Remove-Item Env:BOT_PROXY (и закомментируйте "
            "BOT_PROXY в .env), затем перезапустите бота. Без прокси бот "
            "работает, если api.telegram.org доступен напрямую."
        ) from exc


def is_proxy_available(proxy: str, timeout: float = 2.0) -> bool:
    """``True``, если прокси из ``BOT_PROXY`` принимает соединения."""
    try:
        check_proxy_available(proxy, timeout=timeout)
    except ProxyUnavailableError:
        return False
    return True


def mask_proxy(proxy: str | None) -> str:
    """Безопасное представление прокси для логов (без логина/пароля)."""
    if not proxy:
        return "не задан"
    parts = urlsplit(proxy if "://" in proxy else f"http://{proxy}")
    if parts.username or parts.password:
        host = parts.hostname or "?"
        port = f":{parts.port}" if parts.port else ""
        return f"{parts.scheme}://***@{host}{port}"
    return proxy


def is_proxy_error(exc: BaseException) -> bool:
    """Похоже ли исключение (с цепочкой причин) на проблему с прокси."""
    current: BaseException | None = exc
    for _ in range(10):
        if current is None:
            return False
        if "proxy" in type(current).__name__.lower():
            return True
        if "proxy" in str(current).lower():
            return True
        current = current.__cause__ or current.__context__
    return False


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
        try:
            check_proxy_available(proxy)
        except ProxyUnavailableError as exc:
            # Переменная окружения BOT_PROXY часто остаётся «в наследство» от
            # VPN-сессии, а прокси-клиент уже не запущен. По умолчанию не
            # падаем, а идём напрямую (отключается BOT_PROXY_FALLBACK_DIRECT=false).
            if not getattr(settings.bot, "proxy_fallback", True):
                raise
            logger.warning(
                "{} Продолжаю без прокси: BOT_PROXY_FALLBACK_DIRECT=true.",
                exc,
            )
            return AiohttpSession(timeout=timeout)
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
