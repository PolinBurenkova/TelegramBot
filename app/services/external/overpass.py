"""Overpass API (OpenStreetMap) — объекты рядом (ключ не нужен).

Назначение: отдать ближайшие названные объекты OSM (название, координаты,
категория) для точки. Overpass QL передаётся GET-параметром ``data`` —
POST базовый ``get_json`` не поддерживает.
Ключ не требуется.
API: https://overpass-api.de/api/interpreter
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_URL = "https://overpass-api.de/api/interpreter"


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


def _center_coord(element: dict[str, Any], key: str) -> float | None:
    """Координата из ``center`` (для way/relation в ответе Overpass)."""
    center = element.get("center")
    if not isinstance(center, dict):
        return None
    return _as_coord(center.get(key))


def _node_query(lat: float, lon: float, radius: int, limit: int) -> str:
    """Overpass QL: названные объекты в радиусе вокруг точки."""
    return (
        "[out:json][timeout:20];"
        f"node(around:{radius},{lat},{lon})[name];"
        f"out body {limit};"
    )


class OverpassProvider(BaseProvider):
    """Overpass API: /api/interpreter?data=<QL>, без ключа."""

    name = "overpass"
    category = "poi"
    requires_key = False

    async def fetch(
        self,
        lat: float,
        lon: float,
        radius: int = 1000,
        limit: int = 10,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Объекты OSM рядом; None при пустом ответе."""
        query = str(kwargs.get("query") or _node_query(lat, lon, radius, limit))
        try:
            payload = await self.get_json(_URL, params={"data": query})
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        elements = payload.get("elements")
        if not isinstance(elements, list):
            return None
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = element.get("tags")
            if not isinstance(tags, dict):
                continue
            name = _as_text(tags.get("name"))
            if not name or name in seen:
                continue
            place_lat = _as_coord(element.get("lat")) or _center_coord(element, "lat")
            place_lon = _as_coord(element.get("lon")) or _center_coord(element, "lon")
            if place_lat is None or place_lon is None:
                continue
            category = (
                _as_text(tags.get("amenity"))
                or _as_text(tags.get("tourism"))
                or _as_text(tags.get("historic"))
                or _as_text(tags.get("shop"))
                or _as_text(tags.get("leisure"))
            )
            seen.add(name)
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
