"""OpenCage — геокодинг (требует ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class OpenCageProvider(BaseProvider):
    """Geocoder API OpenCage Data."""

    name = "opencage"
    category = "cities"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        key = get_settings().opencage_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        payload = await self.get_json(
            "https://api.opencagedata.com/geocode/v1/json",
            params={
                "q": query,
                "key": self.api_key,
                "limit": 1,
                "language": "ru",
                "no_annotations": 1,
            },
        )
        results = payload.get("results") or []
        if not results:
            return None
        geom = results[0].get("geometry") or {}
        if geom.get("lat") is None or geom.get("lng") is None:
            return None
        components = results[0].get("components") or {}
        return {
            "geonames_id": None,
            "name": query,
            "name_ru": query,
            "country_code": components.get("country_code"),
            "country_name": components.get("country"),
            "lat": float(geom["lat"]),
            "lon": float(geom["lng"]),
            "population": None,
            "timezone": None,
            "source": "opencage",
        }
