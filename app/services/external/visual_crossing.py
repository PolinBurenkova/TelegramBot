"""Visual Crossing — погода (требует ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class VisualCrossingProvider(BaseProvider):
    """Timeline API Visual Crossing Weather."""

    name = "visual_crossing"
    category = "weather"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        key = get_settings().visual_crossing_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        payload = await self.get_json(
            f"https://weather.visualcrossing.com/VisualCrossingWebServices"
            f"/rest/services/timeline/{lat},{lon}",
            params={
                "key": self.api_key,
                "unitGroup": "metric",
                "include": "current",
                "lang": "ru",
            },
        )
        current = payload.get("currentConditions") or {}
        if not current:
            return None
        return {
            "temp": current.get("temp"),
            "feels_like": current.get("feelslike"),
            "description": current.get("conditions"),
            "icon": None,
            "humidity": current.get("humidity"),
            "wind": current.get("windspeed"),
        }
