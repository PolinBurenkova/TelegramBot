"""Weatherbit — текущая погода. Нужен ключ WEATHERBIT_API_KEY."""
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


class WeatherbitProvider(BaseProvider):
    """Current Weather API Weatherbit: погода по координатам (units=M)."""

    name = "weatherbit"
    category = "weather"
    requires_key = True
    base_url = "https://api.weatherbit.io/v2.0/current"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (WEATHERBIT_API_KEY)."""
        key = get_settings().weatherbit_api_key
        return key.get_secret_value() if key else provider_key("weatherbit")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "lat": lat,
                "lon": lon,
                "key": self.api_key,
                "units": "M",
                "lang": "ru",
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            return None
        items = payload.get("data") or []
        if not isinstance(items, list) or not items:
            return None
        item = items[0]
        if not isinstance(item, dict):
            return None
        weather = item.get("weather")
        if not isinstance(weather, dict):
            weather = {}
        return {
            "temp": _to_float(item.get("temp")),
            "feels_like": _to_float(item.get("app_temp")),
            "description": weather.get("description"),
            "icon": weather.get("icon"),
            "humidity": _to_int(item.get("rh")),
            "wind": _to_float(item.get("wind_spd")),
        }
