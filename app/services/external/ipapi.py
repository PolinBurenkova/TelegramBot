"""IP-геолокация без ключа: ipapi.co, резерв — ip-api.com.

Основной endpoint: ``https://ipapi.co/{ip}/json/`` (без ``ip`` — адрес
вызывающего: ``https://ipapi.co/json/``). Резервный источник —
``http://ip-api.com/json/{ip}`` (бесплатный тариф ip-api.com работает только
по HTTP). Контракт:
``{"ip", "country_code", "city", "lat", "lon", "source"}``;
неудача обоих источников → ``None``.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from loguru import logger

from app.services.external.base import BaseProvider, provider_key


def _to_float(value: Any) -> float | None:
    """Привести значение к float; None/мусор → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class IPApiProvider(BaseProvider):
    """Геолокация по IP: ключ не нужен (у ipapi.co ~1000 запросов в сутки)."""

    name = "ipapi"
    category = "ip_geo"
    requires_key = False

    @property
    def api_key(self) -> str | None:
        """Ключ не требуется; свойство оставлено для единого контракта."""
        return provider_key("ipapi")

    async def fetch(
        self, ip: str | None = None, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Определить страну/город по ``ip`` (``None`` — адрес вызывающего)."""
        target = (ip or "").strip()
        if target:
            url = f"https://ipapi.co/{quote(target, safe='')}/json/"
        else:
            url = "https://ipapi.co/json/"
        try:
            payload = await self.get_json(url)
        except Exception as exc:
            logger.warning("{}: ipapi.co недоступен ({}), пробую ip-api.com", self.name, exc)
            return await self._fetch_fallback(target)
        if not isinstance(payload, dict) or payload.get("error"):
            return await self._fetch_fallback(target)
        return {
            "ip": payload.get("ip") or target or None,
            "country_code": payload.get("country_code"),
            "city": payload.get("city"),
            "lat": _to_float(payload.get("latitude")),
            "lon": _to_float(payload.get("longitude")),
            "source": self.name,
        }

    async def _fetch_fallback(self, ip: str) -> dict[str, Any] | None:
        """Резервный источник ip-api.com (HTTP, без ключа)."""
        if ip:
            url = f"http://ip-api.com/json/{quote(ip, safe='')}"
        else:
            url = "http://ip-api.com/json/"
        try:
            payload = await self.get_json(url)
        except Exception as exc:
            logger.warning("{}: ip-api.com тоже недоступен: {}", self.name, exc)
            return None
        if not isinstance(payload, dict) or payload.get("status") != "success":
            return None
        return {
            "ip": payload.get("query") or ip or None,
            "country_code": payload.get("countryCode"),
            "city": payload.get("city"),
            "lat": _to_float(payload.get("lat")),
            "lon": _to_float(payload.get("lon")),
            "source": self.name,
        }
