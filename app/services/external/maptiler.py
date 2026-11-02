"""MapTiler — статическая карта. Нужен ключ MAPTILER_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class MapTilerProvider(BaseProvider):
    """Static Maps API MapTiler (streets-v2): URL собирается без HTTP."""

    name = "maptiler"
    category = "maps"
    requires_key = True
    base_url = "https://api.maptiler.com/maps/streets-v2/static"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (MAPTILER_API_KEY)."""
        key = get_settings().maptiler_api_key
        return key.get_secret_value() if key else provider_key("maptiler")

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
            f"{self.base_url}/{lon},{lat},{zoom}/{width}x{height}.png"
            f"?key={key}"
        )
        return {"image_url": image_url, "lat": lat, "lon": lon, "source": self.name}
