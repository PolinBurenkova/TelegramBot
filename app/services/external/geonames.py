"""GeoNames — поиск городов (нужен бесплатный username)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.geonames import GeoNamesResponse
from app.services.external.base import BaseProvider


class GeoNamesProvider(BaseProvider):
    """searchJSON GeoNames. Регистрация бесплатна (geonames.org)."""

    name = "geonames"
    category = "cities"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        return get_settings().geonames_username or None

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        payload = await self.get_json(
            "http://api.geonames.org/searchJSON",
            params={
                "q": query,
                "username": self.api_key,
                "maxRows": 1,
                "featureClass": "P",
                "orderby": "population",
            },
        )
        data = GeoNamesResponse.model_validate(payload)
        if data.status or not data.geonames:
            return None
        city = data.geonames[0]
        timezone = city.timezone or {}
        return {
            "geonames_id": city.geoname_id,
            "name": city.name,
            "name_ru": city.name,
            "country_code": city.country_code,
            "country_name": city.country_name,
            "lat": float(city.lat) if city.lat else None,
            "lon": float(city.lng) if city.lng else None,
            "population": city.population,
            "timezone": timezone.get("timeZoneId"),
            "source": "geonames",
        }
