"""OpenWeatherMap — погода (требует ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.owm import OWMResponse
from app.services.external.base import BaseProvider


class OpenWeatherProvider(BaseProvider):
    """Current weather API OpenWeatherMap."""

    name = "openweather"
    category = "weather"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        key = get_settings().openweather_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        payload = await self.get_json(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "ru",
            },
        )
        data = OWMResponse.model_validate(payload)
        if data.main is None:
            return None
        weather = (data.weather or [{}])[0]
        return {
            "temp": data.main.temp,
            "feels_like": data.main.feels_like,
            "description": weather.description,
            "icon": weather.icon,
            "humidity": data.main.humidity,
            "wind": data.wind.speed if data.wind else None,
        }
