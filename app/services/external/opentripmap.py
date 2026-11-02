"""OpenTripMap — достопримечательности рядом (нужен ключ).

Назначение: отдать ближайшие POI (название, координаты, категория) для точки.
Ключ обязателен: ``OPENTRIPMAP_API_KEY`` (параметр ``apikey``).
https://api.opentripmap.com/0.1/ru/places/radius
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://api.opentripmap.com/0.1/ru/places/radius"


def _as_text(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_coord(value: Any) -> float | None:
    """Координата как float, иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class OpenTripMapProvider(BaseProvider):
    """OpenTripMap: /0.1/ru/places/radius, ключ OPENTRIPMAP_API_KEY."""

    name = "opentripmap"
    category = "poi"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения."""
        return provider_key("opentripmap")

    async def fetch(
        self,
        lat: float,
        lon: float,
        radius: int = 1000,
        limit: int = 10,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Объекты поблизости; None без ключа или при пустом списке.

        Запрашиваем не больше лимита записей: у OpenTripMap бесплатный
        тариф ограничен 5 запросами в секунду и 5000 в сутки.
        """
        if not self.api_key:
            return None
        try:
            payload = await self.get_json(
                _URL,
                params={
                    "radius": radius,
                    "lat": lat,
                    "lon": lon,
                    "limit": limit,
                    "format": "json",
                    "apikey": self.api_key,
                },
            )
        except (ExternalAPIError, RateLimitError):
            return None
        if isinstance(payload, dict):
            features = payload.get("features")
            if isinstance(features, list):
                raw_items: list[Any] = features
            else:
                candidate = payload.get("items") or payload.get("places")
                raw_items = candidate if isinstance(candidate, list) else []
        elif isinstance(payload, list):
            raw_items = payload
        else:
            return None
        items: list[dict[str, Any]] = []
        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("properties"), dict):
                properties = entry["properties"]
                geometry = entry.get("geometry")
                coordinates = (
                    geometry.get("coordinates") if isinstance(geometry, dict) else None
                )
                lon_raw = (
                    coordinates[0]
                    if isinstance(coordinates, list) and coordinates
                    else None
                )
                lat_raw = (
                    coordinates[1]
                    if isinstance(coordinates, list) and len(coordinates) > 1
                    else None
                )
                name = _as_text(properties.get("name"))
                category = _as_text(properties.get("kinds"))
                place_lat = _as_coord(lat_raw)
                place_lon = _as_coord(lon_raw)
            else:
                name = _as_text(entry.get("name"))
                category = _as_text(entry.get("kinds"))
                point = entry.get("point")
                if not isinstance(point, dict):
                    point = {}
                place_lat = _as_coord(point.get("lat"))
                place_lon = _as_coord(point.get("lon"))
            if not name or place_lat is None or place_lon is None:
                continue
            if category:
                category = category.split(",")[0].strip() or None
            items.append(
                {
                    "name": name,
                    "lat": place_lat,
                    "lon": place_lon,
                    "category": category,
                }
            )
            if len(items) >= limit:
                break
        if not items:
            return None
        return {"items": items, "source": self.name}
