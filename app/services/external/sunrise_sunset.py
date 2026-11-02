"""Sunrise-Sunset — восход и закат точки (ключ не нужен).

Назначение: отдать время восхода/заката для точки. API не сообщает таймзону,
поэтому ``timezone`` и ``utc_offset`` всегда None, а времена приходят строками
в UTC (параметр ``date`` — на конкретную дату, по умолчанию на завтра).
Ключ не требуется. API: https://api.sunrise-sunset.org/json
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_URL = "https://api.sunrise-sunset.org/json"


def _as_str(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class SunriseSunsetProvider(BaseProvider):
    """Sunrise-Sunset: /json?lat=&lng=, без ключа."""

    name = "sunrise_sunset"
    category = "timezone"
    requires_key = False

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        """Восход/закат для координаты; таймзону API не сообщает (None)."""
        params: dict[str, Any] = {
            "lat": lat,
            "lng": lon,
            "formatted": 0,
            "date": _as_str(kwargs.get("date"))
            or (date.today() + timedelta(days=1)).isoformat(),
        }
        try:
            payload = await self.get_json(_URL, params=params)
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        body = payload.get("results")
        if not isinstance(body, dict):
            return None
        sunrise = _as_str(body.get("sunrise"))
        sunset = _as_str(body.get("sunset"))
        if not sunrise and not sunset:
            return None
        return {
            "timezone": None,
            "utc_offset": None,
            "abbreviation": None,
            "sunrise": sunrise,
            "sunset": sunset,
            "source": self.name,
        }
