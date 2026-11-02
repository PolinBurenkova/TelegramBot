"""Mapbox Static Images — статическая карта. Нужен ключ MAPBOX_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class MapboxProvider(BaseProvider):
    """Static Images API Mapbox (streets-v12): URL собирается без HTTP."""

    name = "mapbox"
    category = "maps"
    requires_key = True
    base_url = "https://api.mapbox.com/styles/v1/mapbox/streets-v12/static"

    @property
    def api_key(self) -> str | None:
        """Токен из Settings, иначе из окружения (MAPBOX_API_KEY)."""
        key = get_settings().mapbox_token
        return key.get_secret_value() if key else provider_key("mapbox")

    async def fetch(
        self,
        lat: float,
        lon: float,
        zoom: int = 12,
        width: int = 600,
        height: int = 400,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        key = self.api_key
        if not key:
            return None
        image_url = (
            f"{self.base_url}/{lon},{lat},{zoom}/{width}x{height}"
            f"?access_token={key}"
        )
        return {"image_url": image_url, "lat": lat, "lon": lon, "source": self.name}
