"""Weatherstack — текущая погода. Нужен ключ WEATHERSTACK_API_KEY."""
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


class WeatherstackProvider(BaseProvider):
    """Current Weather API Weatherstack: погода по координатам."""

    name = "weatherstack"
    category = "weather"
    requires_key = True
    base_url = "https://api.weatherstack.com/current"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (WEATHERSTACK_API_KEY)."""
        key = get_settings().weatherstack_api_key
        return key.get_secret_value() if key else provider_key("weatherstack")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "access_key": self.api_key,
                "query": f"{lat},{lon}",
                "units": "m",
                "language": "ru",
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            return None
        current = payload.get("current")
        if not isinstance(current, dict):
            return None
        descriptions = current.get("weather_descriptions") or []
        icons = current.get("weather_icons") or []
        return {
            "temp": _to_float(current.get("temperature")),
            "feels_like": _to_float(current.get("feelslike")),
            "description": descriptions[0] if descriptions else None,
            "icon": icons[0] if icons else None,
            "humidity": _to_int(current.get("humidity")),
            "wind": _to_float(current.get("wind_speed")),
        }
