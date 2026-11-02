"""Abstract IP Geolocation — геолокация по IP (ключ ``ABSTRACT_API_KEY``).

Endpoint: ``https://ipgeolocation.abstractapi.com/v1/``. Ключ передаётся
параметром ``api_key`` (в ``app/config.py`` это поле ``abstract_api_key``).
Контракт: ``{"ip", "country_code", "city", "lat", "lon", "source"}``;
пустой ответ → ``None``.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider, provider_key


def _to_float(value: Any) -> float | None:
    """Привести значение к float; None/мусор → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class AbstractAPIProvider(BaseProvider):
    """IP Geolocation API от Abstract: ключ обязателен."""

    name = "abstract_api"
    category = "ip_geo"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ ``ABSTRACT_API_KEY``."""
        return provider_key("abstract")

    async def fetch(
        self, ip: str | None = None, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Определить страну/город по ``ip`` (``None`` — адрес вызывающего)."""
        if not self.api_key:
            return None
        target = (ip or "").strip()
        params: dict[str, Any] = {"api_key": self.api_key}
        if target:
            params["ip_address"] = target
        payload = await self.get_json(
            "https://ipgeolocation.abstractapi.com/v1/", params=params
        )
        if not isinstance(payload, dict) or not payload or payload.get("error"):
            return None
        return {
            "ip": payload.get("ip_address") or target or None,
            "country_code": payload.get("country_code"),
            "city": payload.get("city"),
            "lat": _to_float(payload.get("latitude")),
            "lon": _to_float(payload.get("longitude")),
            "source": self.name,
        }
