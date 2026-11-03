"""Тесты предварительной проверки прокси из BOT_PROXY.

Прокси-клиент (v2rayN/xray) часто не запущен, и тогда aiohttp_socks падает с
ProxyConnectionError и длинным трейсбеком. `create_session()` проверяет порт
заранее: по умолчанию продолжает без прокси (`BOT_PROXY_FALLBACK_DIRECT=true`),
а в строгом режиме бросает `ProxyUnavailableError` с понятной подсказкой.
"""
from __future__ import annotations

import pytest

from app.bot.bot_factory import (
    check_proxy_available,
    create_session,
    is_proxy_available,
    is_proxy_error,
    mask_proxy,
    proxy_endpoint,
)
from app.exceptions import ProxyUnavailableError


class _BotView:
    def __init__(self, proxy: str | None, proxy_fallback: bool = True) -> None:
        self.proxy = proxy
        self.proxy_fallback = proxy_fallback
        self.request_timeout = 5.0


class _SettingsStub:
    def __init__(self, proxy: str | None, proxy_fallback: bool = True) -> None:
        self.bot = _BotView(proxy, proxy_fallback)


def test_proxy_endpoint_parses_socks_scheme() -> None:
    assert proxy_endpoint("socks5://127.0.0.1:10808") == ("127.0.0.1", 10808)


def test_proxy_endpoint_uses_default_port() -> None:
    assert proxy_endpoint("http://proxy.local") == ("proxy.local", 8080)
    assert proxy_endpoint("socks5://proxy.local") == ("proxy.local", 1080)


def test_check_proxy_available_raises_when_port_closed() -> None:
    # Порт 1 на localhost гарантированно закрыт — соединение отклоняется сразу.
    with pytest.raises(ProxyUnavailableError) as info:
        check_proxy_available("socks5://127.0.0.1:1", timeout=0.5)

    assert "127.0.0.1:1" in str(info.value)
    assert "BOT_PROXY" in str(info.value)


def test_check_proxy_available_rejects_empty_host() -> None:
    with pytest.raises(ProxyUnavailableError):
        check_proxy_available("socks5://:1080")


def test_is_proxy_available_false_for_closed_port() -> None:
    assert is_proxy_available("socks5://127.0.0.1:1", timeout=0.5) is False


def test_create_session_falls_back_to_direct_without_proxy() -> None:
    """Дефолт: недоступный прокси — предупреждение и работа напрямую."""
    session = create_session(_SettingsStub("socks5://127.0.0.1:1"))  # type: ignore[arg-type]

    assert type(session).__name__ == "AiohttpSession"


def test_create_session_strict_mode_raises_on_dead_proxy() -> None:
    settings = _SettingsStub("socks5://127.0.0.1:1", proxy_fallback=False)

    with pytest.raises(ProxyUnavailableError):
        create_session(settings)  # type: ignore[arg-type]


def test_is_proxy_error_detects_wrapped_error() -> None:
    inner = RuntimeError("Cannot connect to host proxy.local:1080")
    outer = RuntimeError("request failed")
    outer.__cause__ = inner

    assert is_proxy_error(outer)


def test_is_proxy_error_ignores_plain_error() -> None:
    assert not is_proxy_error(ValueError("bad city"))


def test_mask_proxy_keeps_plain_url() -> None:
    assert mask_proxy(None) == "не задан"
    assert mask_proxy("socks5://127.0.0.1:10808") == "socks5://127.0.0.1:10808"


def test_mask_proxy_hides_credentials() -> None:
    masked = mask_proxy("http://user:secret@proxy.local:8080")

    assert "user" not in masked
    assert "secret" not in masked
    assert "proxy.local:8080" in masked
