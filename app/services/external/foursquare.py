"""Foursquare Places — поиск мест рядом (нужен ключ).

Назначение: отдать ближайшие POI (название, координаты, категория) для точки.
Ключ обязателен: ``FOURSQUARE_API_KEY`` (заголовок ``Authorization``).
https://api.foursquare.com/v3/places/search
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://api.foursquare.com/v3/places/search"


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


def _category(item: dict[str, Any]) -> str | None:
    """Название первой категории места (если API её вернул)."""
    categories = item.get("categories")
    if not isinstance(categories, list) or not categories:
        return None
    first = categories[0]
    if not isinstance(first, dict):
        return None
    return _as_text(first.get("name"))


class FoursquareProvider(BaseProvider):
    """Foursquare Places v3: /v3/places/search, ключ FOURSQUARE_API_KEY."""

    name = "foursquare"
    category = "poi"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения."""
        return provider_key("foursquare")

    async def fetch(
        self,
        lat: float,
        lon: float,
        radius: int = 1000,
        limit: int = 10,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Ближайшие места; None без ключа или при пустом списке."""
        if not self.api_key:
            return None
        try:
            payload = await self.get_json(
                _URL,
                params={
                    "ll": f"{lat},{lon}",
                    "radius": radius,
                    "limit": limit,
                    "sort": "DISTANCE",
                },
            )
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        results = payload.get("results")
        if not isinstance(results, list):
            return None
        items: list[dict[str, Any]] = []
        for entry in results:
            if not isinstance(entry, dict):
                continue
            name = _as_text(entry.get("name"))
            if not name:
                continue
            geocodes = entry.get("geocodes")
            main = geocodes.get("main") if isinstance(geocodes, dict) else None
            if not isinstance(main, dict):
                main = {}
            place_lat = _as_coord(main.get("latitude"))
            place_lon = _as_coord(main.get("longitude"))
            if place_lat is None or place_lon is None:
                continue
            item_category = _category(entry)
            items.append(
                {
                    "name": name,
                    "lat": place_lat,
                    "lon": place_lon,
                    "category": item_category,
                }
            )
            if len(items) >= limit:
                break
        if not items:
            return None
        return {"items": items, "source": self.name}
