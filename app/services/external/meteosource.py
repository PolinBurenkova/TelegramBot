"""Meteosource — текущая погода. Нужен ключ METEOSOURCE_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


def _to_float(value: Any) -> float | None:
    """Число к float; мусор и пустое значение → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    """Число (влажность) к int; мусор и пустое значение → None."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class MeteosourceProvider(BaseProvider):
    """Free Point API Meteosource: секция current по координатам."""

    name = "meteosource"
    category = "weather"
    requires_key = True
    base_url = "https://api.meteosource.com/v1/free/point"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (METEOSOURCE_API_KEY)."""
        key = get_settings().meteosource_api_key
        return key.get_secret_value() if key else provider_key("meteosource")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "lat": lat,
                "lon": lon,
                "sections": "current",
                "units": "metric",
                "language": "ru",
                "key": self.api_key,
            },
        )
        if not isinstance(payload, dict):
            return None
        current = payload.get("current")
        if not isinstance(current, dict):
            return None
        wind = current.get("wind")
        wind_speed = wind.get("speed") if isinstance(wind, dict) else None
        icon = current.get("icon")
        return {
            "temp": _to_float(current.get("temperature")),
            "feels_like": _to_float(current.get("feels_like")),
            "description": current.get("summary"),
            "icon": str(icon) if icon is not None else None,
            "humidity": _to_int(current.get("humidity")),
            "wind": _to_float(wind_speed),
        }
