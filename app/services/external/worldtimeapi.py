"""WorldTimeAPI — таймзона и UTC-смещение точки (ключ не нужен).

Назначение: отдать таймзону, UTC-смещение и аббревиатуру для координат
(``/ip`` — по IP запроса) либо для явно указанной IANA-таймзоны.
Ключ не требуется. API: https://worldtimeapi.org/api
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_BASE_URL = "https://worldtimeapi.org/api"


def _as_int(value: Any) -> int | None:
    """Привести utc_offset к int (секунды), иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class WorldTimeAPIProvider(BaseProvider):
    """WorldTimeAPI: /timezone/{tz} и /ip, без ключа."""

    name = "worldtimeapi"
    category = "timezone"
    requires_key = False

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        timezone: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Таймзона/смещение по координатам (``/ip``) или по IANA-имени."""
        tz = _as_str(timezone) or _as_str(kwargs.get("tz"))
        url = f"{_BASE_URL}/timezone/{tz}" if tz else f"{_BASE_URL}/ip"
        try:
            payload = await self.get_json(url)
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        name = _as_str(payload.get("timezone"))
        offset = _as_int(payload.get("raw_offset"))
        if offset is None:
            offset = _as_int(payload.get("utc_offset"))
        abbreviation = _as_str(payload.get("abbreviation"))
        if not any((name, offset is not None, abbreviation)):
            return None
        return {
            "timezone": name,
            "utc_offset": offset,
            "abbreviation": abbreviation,
            "sunrise": None,
            "sunset": None,
            "source": self.name,
        }
