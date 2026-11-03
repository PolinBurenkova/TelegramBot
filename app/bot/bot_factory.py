"""Create configured Bot instance and register the command menu."""
from __future__ import annotations

import importlib.util
import socket
from collections.abc import Awaitable, Callable
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

#: Транспорты до api.telegram.org.
TRANSPORTS: frozenset[str] = frozenset({"auto", "direct", "proxy"})

_PROXY_DEFAULT_PORTS: dict[str, int] = {
    "http": 8080,
    "https": 8080,
    "socks4": 1080,
    "socks4h": 1080,
    "socks5": 1080,
    "socks5h": 1080,
}

_SOCKS_SCHEMES: tuple[str, ...] = ("socks4://", "socks5://", "socks4h://", "socks5h://")


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
            "в PowerShell — Remove-Item Env:BOT_PROXY, в .env закомментируйте "
            "BOT_PROXY, затем перезапустите бота. Если включён обычный VPN, "
            "прокси не нужен вовсе (BOT_TRANSPORT=auto пойдёт напрямую)."
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


def _require_socks_support(proxy: str) -> None:
    """Понятная ошибка, если выбран socks-прокси, а пакета нет."""
    if proxy.startswith(_SOCKS_SCHEMES) and importlib.util.find_spec("aiohttp_socks") is None:
        raise RuntimeError(
            "Для socks-прокси нужен пакет aiohttp_socks: "
            "pip install aiohttp_socks (или укажите http://-прокси в BOT_PROXY)"
        )


def create_session(settings: Settings, transport: str | None = None) -> BaseSession:
    """Сессия Telegram с учётом транспорта, прокси и таймаута.

    ``transport`` (по умолчанию ``BOT_TRANSPORT``):
      * ``direct`` — напрямую. Обычный системный VPN просто маршрутизирует
        трафик сам, боту отдельная настройка не нужна;
      * ``proxy``  — только через ``BOT_PROXY``, при недоступности падаем;
      * ``auto``   — прокси используется, только если он реально отвечает.
    """
    # AiohttpSession → BaseSession принимает timeout как float (секунды),
    # а не ClientTimeout: см. aiogram/client/session/base.py::BaseSession.
    timeout = float(settings.bot.request_timeout)
    mode = (transport or getattr(settings.bot, "transport", "auto") or "auto").lower()
    proxy = settings.bot.proxy

    if mode == "direct":
        if proxy:
            logger.info("Транспорт: прямое соединение, BOT_PROXY игнорируется")
        return AiohttpSession(timeout=timeout)

    if mode == "proxy":
        if not proxy:
            raise ProxyUnavailableError(
                "BOT_TRANSPORT=proxy, но BOT_PROXY не задан. Укажите адрес прокси "
                "(например socks5://127.0.0.1:10808) или верните BOT_TRANSPORT=auto."
            )
        _require_socks_support(proxy)
        check_proxy_available(proxy)
        return AiohttpSession(proxy=proxy, timeout=timeout)

    # auto: прокси — только если он жив, иначе прямое соединение (VPN).
    if not proxy:
        return AiohttpSession(timeout=timeout)
    _require_socks_support(proxy)
    try:
        check_proxy_available(proxy)
    except ProxyUnavailableError as exc:
        # BOT_PROXY часто остаётся «в наследство» от VPN-сессии, а прокси-клиент
        # уже не запущен. Не падаем, а идём напрямую (строгий режим —
        # BOT_PROXY_FALLBACK_DIRECT=false).
        if not getattr(settings.bot, "proxy_fallback", True):
            raise
        logger.warning("{} Продолжаю без прокси (BOT_TRANSPORT=auto).", exc)
        return AiohttpSession(timeout=timeout)
    return AiohttpSession(proxy=proxy, timeout=timeout)


async def probe_direct(settings: Settings) -> bool:
    """Доступен ли api.telegram.org напрямую (включён обычный VPN).

    Отдельная короткая сессия без прокси: успешный ``getMe`` значит, что
    транспорт рабочий. ``401`` тоже считается успехом — значит связь есть, а
    проблема только в токене (её покажет основной запуск).
    """
    probe_timeout = min(10.0, float(settings.bot.request_timeout))
    session = AiohttpSession(timeout=probe_timeout)
    bot = Bot(token=settings.bot.token, session=session)
    try:
        await bot.get_me()
        return True
    except TelegramUnauthorizedError:
        return True
    except Exception:  # noqa: BLE001 — любая сетевая ошибка = прямого доступа нет
        return False
    finally:
        try:
            await session.close()
        except Exception:  # noqa: BLE001
            pass


async def detect_transport(
    settings: Settings,
    direct_probe: Callable[[], Awaitable[bool]] | None = None,
    proxy_probe: Callable[[str], bool] | None = None,
) -> str:
    """Выбрать транспорт: прямое соединение (VPN) или прокси.

    ``direct_probe`` и ``proxy_probe`` можно подменить в тестах, чтобы не ходить
    в сеть.
    """
    mode = (settings.bot.transport or "auto").lower()
    if mode in ("direct", "proxy"):
        return mode

    probe = direct_probe or (lambda: probe_direct(settings))
    if await probe():
        return "direct"

    proxy = settings.bot.proxy
    proxy_ok = proxy_probe or is_proxy_available
    if proxy and proxy_ok(proxy):
        return "proxy"
    # Ни VPN, ни прокси не отвечают: идём напрямую, чтобы показать сетевую
    # ошибку с подсказкой, а не «прокси недоступен».
    return "direct"


def create_bot(settings: Settings | None = None, transport: str | None = None) -> Bot:
    """Build Bot. Uses Settings() if not provided."""
    if settings is None:
        settings = Settings()
    return Bot(
        token=settings.bot.token,
        session=create_session(settings, transport=transport),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def create_bot_auto(settings: Settings | None = None) -> Bot:
    """Создать Bot, автоматически выбрав рабочий транспорт (VPN или прокси)."""
    if settings is None:
        settings = Settings()
    transport = await detect_transport(settings)
    if transport == "direct":
        logger.info(
            "Транспорт Telegram: прямое соединение (подходит обычный системный VPN)"
        )
    else:
        logger.info("Транспорт Telegram: прокси {}", mask_proxy(settings.bot.proxy))
    return create_bot(settings, transport=transport)


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
