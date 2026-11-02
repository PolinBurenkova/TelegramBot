"""Mapbox Geocoding — геокодинг городов. Нужен ключ MAPBOX_API_KEY."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


def _to_float(value: Any) -> float | None:
    """Координата к float; мусор и пустое значение → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    """Число (население, id) к int; мусор и пустое значение → None."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _upper(value: Any) -> str | None:
    """Код страны в верхний регистр; не строка → None."""
    return value.strip().upper() if isinstance(value, str) and value.strip() else None


class MapboxGeocodingProvider(BaseProvider):
    """Places API Mapbox: запрос в пути URL, ответ — GeoJSON-фичи."""

    name = "mapbox_geocoding"
    category = "cities"
    requires_key = True
    base_url = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    @property
    def api_key(self) -> str | None:
        """Токен из Settings (geocoding или общий), иначе MAPBOX_API_KEY."""
        settings = get_settings()
        key = settings.mapbox_geocoding_token or settings.mapbox_token
        return key.get_secret_value() if key else provider_key("mapbox")

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            f"{self.base_url}/{quote(query, safe='')}.json",
            params={
                "access_token": self.api_key,
                "limit": 1,
                "language": "ru",
                "types": "place",
            },
        )
        if not isinstance(payload, dict):
            return None
        features = payload.get("features") or []
        if not isinstance(features, list) or not features:
            return None
        feature = features[0]
        if not isinstance(feature, dict):
            return None
        center = feature.get("center") or []
        if not isinstance(center, list) or len(center) < 2:
            return None
        lon = _to_float(center[0])
        lat = _to_float(center[1])
        if lat is None or lon is None:
            return None
        country_code: str | None = None
        country_name: str | None = None
        for context in feature.get("context") or []:
            if not isinstance(context, dict):
                continue
            if str(context.get("id") or "").startswith("country"):
                country_name = context.get("text")
                country_code = _upper(context.get("short_code"))
                break
        properties = feature.get("properties")
        population = properties.get("population") if isinstance(properties, dict) else None
        name = feature.get("text") or query
        return {
            "geonames_id": feature.get("id"),
            "name": name,
            "name_ru": name,
            "country_code": country_code,
            "country_name": country_name,
            "lat": lat,
            "lon": lon,
            "population": _to_int(population),
            "timezone": None,
            "source": self.name,
        }
