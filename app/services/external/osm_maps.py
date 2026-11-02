"""OSM Static Map — статическая карта OpenStreetMap. Ключ не нужен."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class OSMStaticMapProvider(BaseProvider):
    """Static Map сервиса openstreetmap.de: URL собирается без HTTP-запроса."""

    name = "osm_maps"
    category = "maps"
    requires_key = False
    base_url = "https://staticmap.openstreetmap.de/staticmap.php"

    async def fetch(
        self,
        lat: float,
        lon: float,
        zoom: int = 12,
        width: int = 600,
        height: int = 400,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        base = (get_settings().osm_static_base_url or "").rstrip("/")
        if not base:
            base = "https://staticmap.openstreetmap.de"
        image_url = (
            f"{base}/staticmap.php?center={lat},{lon}&zoom={zoom}"
            f"&size={width}x{height}&maptype=mapnik"
        )
        return {"image_url": image_url, "lat": lat, "lon": lon, "source": self.name}
