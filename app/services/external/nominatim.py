"""Nominatim (OpenStreetMap) — геокодинг без ключа (лимит 1 р/с)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.nominatim import NominatimPlace
from app.services.external.base import BaseProvider


class NominatimProvider(BaseProvider):
    """Поиск координат города. Регистрация не требуется."""

    name = "nominatim"
    category = "cities"
    requires_key = False

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        base = get_settings().nominatim_url.rstrip("/")
        payload = await self.get_json(
            f"{base}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "accept-language": "ru",
            },
        )
        if not payload:
            return None
        place = NominatimPlace.model_validate(payload[0])
        if place.lat is None or place.lon is None:
            return None
        return {
            "geonames_id": place.place_id,
            "name": query,
            "name_ru": query,
            "country_code": None,
            "country_name": None,
            "lat": float(place.lat),
            "lon": float(place.lon),
            "population": None,
            "timezone": None,
            "source": "nominatim",
        }
