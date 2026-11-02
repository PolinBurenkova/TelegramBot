"""Thunderforest — статические карты (требует ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class ThunderForestProvider(BaseProvider):
    """Static maps API: картинка карты по координатам."""

    name = "thunderforest"
    category = "maps"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        key = get_settings().thunderforest_api_key
        return key.get_secret_value() if key else None

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
        return {
            "image_url": (
                "https://staticmap.thunderforest.com/"
                f"?center={lat},{lon}&zoom={zoom}"
                f"&size={width}x{height}&apikey={key}"
            ),
            "lat": lat,
            "lon": lon,
            "source": "thunderforest",
        }
