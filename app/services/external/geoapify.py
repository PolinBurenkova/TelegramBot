"""Geoapify — геокодинг городов. Нужен ключ GEOAPIFY_API_KEY."""
from __future__ import annotations

from typing import Any

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


class GeoapifyProvider(BaseProvider):
    """Geocoding API Geoapify: свободный текст → координаты города."""

    name = "geoapify"
    category = "cities"
    requires_key = True
    base_url = "https://api.geoapify.com/v1/geocode/search"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (GEOAPIFY_API_KEY)."""
        key = get_settings().geoapify_api_key
        return key.get_secret_value() if key else provider_key("geoapify")

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "text": query,
                "apiKey": self.api_key,
                "format": "json",
                "limit": 1,
                "lang": "ru",
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
        lat = _to_float(item.get("lat"))
        lon = _to_float(item.get("lon"))
        if lat is None or lon is None:
            return None
        timezone = item.get("timezone")
        tz_name = timezone.get("name") if isinstance(timezone, dict) else timezone
        name = item.get("name") or item.get("city") or item.get("address_line1") or query
        return {
            "geonames_id": item.get("place_id"),
            "name": name,
            "name_ru": name,
            "country_code": _upper(item.get("country_code")),
            "country_name": item.get("country"),
            "lat": lat,
            "lon": lon,
            "population": _to_int(item.get("population")),
            "timezone": tz_name,
            "source": self.name,
        }
