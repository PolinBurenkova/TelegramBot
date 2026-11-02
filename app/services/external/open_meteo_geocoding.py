"""Open-Meteo Geocoding — поиск городов. Ключ не нужен."""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider


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


class OpenMeteoGeocodingProvider(BaseProvider):
    """Geocoding API Open-Meteo: название города → координаты (без ключа)."""

    name = "open_meteo_geocoding"
    category = "cities"
    requires_key = False
    base_url = "https://geocoding-api.open-meteo.com/v1/search"

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        payload = await self.get_json(
            self.base_url,
            params={
                "name": query,
                "count": 1,
                "language": "ru",
                "format": "json",
            },
        )
        if not isinstance(payload, dict):
            return None
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            return None
        item = results[0]
        if not isinstance(item, dict):
            return None
        lat = _to_float(item.get("latitude"))
        lon = _to_float(item.get("longitude"))
        if lat is None or lon is None:
            return None
        name = item.get("name") or query
        return {
            "geonames_id": _to_int(item.get("id")),
            "name": name,
            "name_ru": name,
            "country_code": _upper(item.get("country_code")),
            "country_name": item.get("country"),
            "lat": lat,
            "lon": lon,
            "population": _to_int(item.get("population")),
            "timezone": item.get("timezone"),
            "source": self.name,
        }
