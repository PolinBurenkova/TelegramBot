"""Базовый контракт внешнего провайдера.

Все провайдеры наследуются от BaseProvider и реализуют async fetch(**kwargs).
Каскад (ProviderChain) вызывает provider.fetch(**kwargs) напрямую;
сервисы могут вызывать provider.call("<method>", **kwargs) — имя метода
используется только для журналирования, вызов уходит в fetch.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from loguru import logger

from app.exceptions import ExternalAPIError, RateLimitError
from app.utils.http_client import create_http_session


def provider_key(*names: str) -> str | None:
    """Ключ провайдера из окружения.

    Конвенция: ``<NAME>_API_KEY``, затем ``<NAME>_TOKEN``, ``<NAME>_KEY`` и
    ``<NAME>_USERNAME`` (например, ``WEATHERSTACK_API_KEY``). Для провайдеров,
    у которых поле уже объявлено в ``app/config.py``, используется оно —
    хелпер нужен только для «длинного хвоста», чтобы не раздувать ``Settings``
    на десятки полей. Переменные читаются из окружения (``.env`` подхватывает
    ``python-dotenv`` при старте), поэтому в ``.env.example`` они описаны
    комментарием.
    """
    for name in names:
        prefix = name.upper()
        for suffix in ("API_KEY", "TOKEN", "KEY", "USERNAME"):
            value = os.getenv(f"{prefix}_{suffix}", "").strip()
            if value:
                return value
    return None


class BaseProvider:
    """Базовый класс провайдера внешнего API."""

    name: str = "base"
    category: str = "generic"
    requires_key: bool = False
    base_url: str = ""
    timeout: float = 10.0

    def __init__(
        self,
        http: httpx.AsyncClient | None = None,
        api_key: str | None = None,
    ) -> None:
        self._http = http
        self._api_key = api_key
        # Breaker создаётся ProviderChain при первом вызове (см. _breaker).
        self.breaker: Any | None = None

    # ─── конфигурация ──────────────────────────────────────────────────────

    @property
    def http(self) -> httpx.AsyncClient:
        """HTTP-клиент: injected или общий синглтон приложения."""
        if self._http is None or self._http.is_closed:
            self._http = create_http_session()
        return self._http

    @property
    def api_key(self) -> str | None:
        """API-ключ провайдера (None → ключ не задан)."""
        return self._api_key or None

    @property
    def is_configured(self) -> bool:
        """Провайдер готов к работе (ключ есть, если он требуется)."""
        return not self.requires_key or bool(self.api_key)

    # ─── контракт ──────────────────────────────────────────────────────────

    async def fetch(self, **kwargs: Any) -> Any:
        """Выполнить запрос. По умолчанию — заглушка (None)."""
        return None

    async def call(self, method: str, **kwargs: Any) -> Any:
        """Диспетчер: имя метода только для логов, вызывается fetch."""
        logger.debug("provider {} call method={}", self.name, method)
        return await self.fetch(**kwargs)

    # ─── helpers ───────────────────────────────────────────────────────────

    async def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """GET с приведением ошибок к доменным исключениям."""
        try:
            response = await self.http.get(url, params=params, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise ExternalAPIError(
                f"{self.name}: network error: {exc}", provider=self.name
            ) from exc
        if response.status_code == 429:
            raise RateLimitError(f"{self.name}: rate limited", provider=self.name)
        if response.status_code >= 400:
            raise ExternalAPIError(
                f"{self.name}: HTTP {response.status_code}",
                provider=self.name,
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalAPIError(
                f"{self.name}: invalid JSON", provider=self.name
            ) from exc
