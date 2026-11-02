"""Stadia Maps — статическая карта. Нужен ключ STADIA_MAPS_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class StadiaMapsProvider(BaseProvider):
    """Static Maps API Stadia Maps: URL собирается без HTTP-запроса."""

    name = "stadia_maps"
    category = "maps"
    requires_key = True
    base_url = "https://tiles.stadiamaps.com/static"
    style: str = "alidade_smooth"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (STADIA_MAPS_API_KEY)."""
        key = get_settings().stadia_maps_api_key
        return key.get_secret_value() if key else provider_key("stadia_maps", "stadia")

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
            f"{self.base_url}/{self.style}/{lon},{lat},{zoom}/{width}x{height}.png"
            f"?api_key={key}"
        )
        return {"image_url": image_url, "lat": lat, "lon": lon, "source": self.name}
