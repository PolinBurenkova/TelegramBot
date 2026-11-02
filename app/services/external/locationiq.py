"""LocationIQ — геокодинг городов. Нужен ключ LOCATIONIQ_API_KEY."""
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


class LocationIQProvider(BaseProvider):
    """Search API LocationIQ (US-эндпоинт): город → координаты."""

    name = "locationiq"
    category = "cities"
    requires_key = True
    base_url = "https://us1.locationiq.com/v1/search"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (LOCATIONIQ_API_KEY)."""
        key = get_settings().locationiq_api_key
        return key.get_secret_value() if key else provider_key("locationiq")

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "key": self.api_key,
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
                "accept-language": "ru",
            },
        )
        if not isinstance(payload, list) or not payload:
            return None
        item = payload[0]
        if not isinstance(item, dict):
            return None
        lat = _to_float(item.get("lat"))
        lon = _to_float(item.get("lon"))
        if lat is None or lon is None:
            return None
        address = item.get("address")
        if not isinstance(address, dict):
            address = {}
        name = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or item.get("display_name")
            or query
        )
        return {
            "geonames_id": _to_int(item.get("place_id")),
            "name": name,
            "name_ru": name,
            "country_code": _upper(address.get("country_code")),
            "country_name": address.get("country"),
            "lat": lat,
            "lon": lon,
            "population": None,
            "timezone": None,
            "source": self.name,
        }
