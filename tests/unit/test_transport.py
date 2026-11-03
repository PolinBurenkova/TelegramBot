"""Тесты выбора транспорта до Telegram: VPN (напрямую) или прокси.

`BOT_TRANSPORT=auto` — обычный системный VPN работает без настройки: сначала
пробуем прямое соединение, и только если оно недоступно — локальный прокси.
В тестах сеть подменяется пробами (`direct_probe`, `proxy_probe`).
"""
from __future__ import annotations

import pytest

from app.bot.bot_factory import (
    TRANSPORTS,
    create_session,
    detect_transport,
)
from app.exceptions import ProxyUnavailableError


class _BotView:
    def __init__(self, proxy: str | None, transport: str = "auto", fallback: bool = True) -> None:
        self.proxy = proxy
        self.transport = transport
        self.proxy_fallback = fallback
        self.request_timeout = 5.0


class _SettingsStub:
    def __init__(self, proxy: str | None, transport: str = "auto", fallback: bool = True) -> None:
        self.bot = _BotView(proxy, transport, fallback)


async def _direct_ok() -> bool:
    return True


async def _direct_fail() -> bool:
    return False


def _proxy_ok(_: str) -> bool:
    return True


def _proxy_fail(_: str) -> bool:
    return False


def test_transports_are_known() -> None:
    assert TRANSPORTS == {"auto", "direct", "proxy"}


async def test_explicit_direct_ignores_proxy() -> None:
    settings = _SettingsStub("socks5://127.0.0.1:10808", transport="direct")

    assert await detect_transport(settings) == "direct"  # type: ignore[arg-type]


async def test_explicit_proxy_is_respected() -> None:
    settings = _SettingsStub("socks5://127.0.0.1:10808", transport="proxy")

    assert await detect_transport(settings) == "proxy"  # type: ignore[arg-type]


async def test_auto_prefers_direct_when_vpn_works() -> None:
    settings = _SettingsStub("socks5://127.0.0.1:10808")

    transport = await detect_transport(
        settings,  # type: ignore[arg-type]
        direct_probe=_direct_ok,
        proxy_probe=_proxy_ok,
    )

    assert transport == "direct"


async def test_auto_uses_proxy_when_direct_fails() -> None:
    settings = _SettingsStub("socks5://127.0.0.1:10808")

    transport = await detect_transport(
        settings,  # type: ignore[arg-type]
        direct_probe=_direct_fail,
        proxy_probe=_proxy_ok,
    )

    assert transport == "proxy"


async def test_auto_falls_back_to_direct_without_proxy() -> None:
    settings = _SettingsStub(None)

    transport = await detect_transport(
        settings,  # type: ignore[arg-type]
        direct_probe=_direct_fail,
        proxy_probe=_proxy_fail,
    )

    # Идём напрямую, чтобы показать сетевую ошибку с подсказкой про VPN.
    assert transport == "direct"


def test_direct_session_has_no_proxy() -> None:
    session = create_session(_SettingsStub("socks5://127.0.0.1:10808", transport="direct"))  # type: ignore[arg-type]

    assert type(session).__name__ == "AiohttpSession"


def test_proxy_mode_without_proxy_raises() -> None:
    with pytest.raises(ProxyUnavailableError):
        create_session(_SettingsStub(None, transport="proxy"))  # type: ignore[arg-type]


def test_proxy_mode_with_dead_proxy_raises() -> None:
    settings = _SettingsStub("socks5://127.0.0.1:1", transport="proxy")

    with pytest.raises(ProxyUnavailableError):
        create_session(settings)  # type: ignore[arg-type]
