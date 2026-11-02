"""TimeZoneDB — часовой пояс по координатам (требует бесплатный ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class TimeZoneDBProvider(BaseProvider):
    """GET /v2.1/get-time-zone?by=position — зона, смещение, аббревиатура."""

    name = "timezonedb"
    category = "timezone"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        settings = get_settings()
        configured = getattr(settings, "timezonedb_api_key", None)
        if configured:
            return (
                configured.get_secret_value()
                if hasattr(configured, "get_secret_value")
                else str(configured)
            )
        return provider_key("timezonedb")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        key = self.api_key
        if not key:
            return None
        payload = await self.get_json(
            "https://api.timezonedb.com/v2.1/get-time-zone",
            params={
                "key": key,
                "format": "json",
                "by": "position",
                "lat": lat,
                "lng": lon,
            },
        )
        if not isinstance(payload, dict) or payload.get("status") != "OK":
            return None
        offset = payload.get("gmtOffset")
        return {
            "timezone": payload.get("zoneName"),
            "utc_offset": int(offset) if isinstance(offset, (int, float)) else None,
            "abbreviation": payload.get("abbreviation"),
            "sunrise": None,
            "sunset": None,
            "source": self.name,
        }
