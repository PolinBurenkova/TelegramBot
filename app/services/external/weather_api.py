"""WeatherAPI.com — погода (требует ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class WeatherAPIProvider(BaseProvider):
    """Current conditions WeatherAPI."""

    name = "weather_api"
    category = "weather"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        key = get_settings().weather_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        payload = await self.get_json(
            "https://api.weatherapi.com/v1/current.json",
            params={"q": f"{lat},{lon}", "key": self.api_key, "lang": "ru"},
        )
        current = payload.get("current") or {}
        if not current:
            return None
        return {
            "temp": current.get("temp_c"),
            "feels_like": current.get("feelslike_c"),
            "description": (current.get("condition") or {}).get("text"),
            "icon": None,
            "humidity": current.get("humidity"),
            "wind": current.get("wind_kph"),
        }
