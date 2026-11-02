"""AccuWeather — текущая погода. Нужен ключ ACCUWEATHER_API_KEY."""
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
    """Число (влажность, код иконки) к int; мусор → None."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _metric(block: Any) -> float | None:
    """Значение Metric.Value из вложенного блока AccuWeather."""
    if not isinstance(block, dict):
        return None
    metric = block.get("Metric")
    if not isinstance(metric, dict):
        return None
    return _to_float(metric.get("Value"))


class AccuweatherProvider(BaseProvider):
    """Current Conditions API AccuWeather: geoposition/search → currentconditions."""

    name = "accuweather"
    category = "weather"
    requires_key = True
    base_url = "https://dataservice.accuweather.com"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (ACCUWEATHER_API_KEY)."""
        key = get_settings().accuweather_api_key
        return key.get_secret_value() if key else provider_key("accuweather")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        location = await self.get_json(
            f"{self.base_url}/locations/v1/cities/geoposition/search",
            params={"apikey": self.api_key, "q": f"{lat},{lon}", "language": "ru"},
        )
        if not isinstance(location, dict):
            return None
        location_key = location.get("Key")
        if not location_key:
            return None
        payload = await self.get_json(
            f"{self.base_url}/currentconditions/v1/{location_key}",
            params={"apikey": self.api_key, "details": "true", "language": "ru"},
        )
        if not isinstance(payload, list) or not payload:
            return None
        item = payload[0]
        if not isinstance(item, dict):
            return None
        wind = item.get("Wind")
        wind_speed = _metric(wind.get("Speed")) if isinstance(wind, dict) else None
        icon = _to_int(item.get("WeatherIcon"))
        return {
            "temp": _metric(item.get("Temperature")),
            "feels_like": _metric(item.get("RealFeelTemperature")),
            "description": item.get("WeatherText"),
            "icon": str(icon) if icon is not None else None,
            "humidity": _to_int(item.get("RelativeHumidity")),
            "wind": wind_speed,
        }
