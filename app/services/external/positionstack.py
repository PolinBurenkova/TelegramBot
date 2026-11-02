"""Positionstack — геокодинг городов. Нужен ключ POSITIONSTACK_API_KEY."""
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


class PositionstackProvider(BaseProvider):
    """Forward Geocoding API Positionstack: название города → координаты."""

    name = "positionstack"
    category = "cities"
    requires_key = True
    base_url = "https://api.positionstack.com/v1/forward"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (POSITIONSTACK_API_KEY)."""
        key = get_settings().positionstack_api_key
        return key.get_secret_value() if key else provider_key("positionstack")

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "access_key": self.api_key,
                "query": query,
                "limit": 1,
                "output": "json",
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            return None
        items = payload.get("data") or []
        if not isinstance(items, list) or not items:
            return None
        item = items[0]
        if not isinstance(item, dict):
            return None
        lat = _to_float(item.get("latitude"))
        lon = _to_float(item.get("longitude"))
        if lat is None or lon is None:
            return None
        name = item.get("name") or item.get("label") or query
        return {
            "geonames_id": None,
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
