"""USGS Earthquake Hazards Program — землетрясения рядом (ключ не нужен).

Назначение: отдать последние землетрясения в радиусе от точки в формате
GeoJSON. Каждый элемент — ``{"title", "url", "date", "description"}``,
где description содержит магнитуду и место.
Ключ не требуется.
API: https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def _as_text(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    """Число как float, иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_date(value: Any) -> str | None:
    """Метка времени в ISO-8601 (UTC) из unix-миллисекунд."""
    number = _as_float(value)
    if number is None:
        return None
    try:
        moment = datetime.fromtimestamp(number / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return moment.isoformat()


class USGSEarthquakeProvider(BaseProvider):
    """USGS FDSN: /fdsnws/event/1/query, без ключа."""

    name = "usgs_earthquake"
    category = "nature"
    requires_key = False

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Землетрясения рядом; None, если событий нет."""
        params: dict[str, Any] = {
            "format": "geojson",
            "limit": 10,
            "orderby": "time",
        }
        radius_km = _as_float(kwargs.get("maxradiuskm"))
        if lat is not None and lon is not None:
            params["latitude"] = lat
            params["longitude"] = lon
            params["maxradiuskm"] = radius_km if radius_km is not None else 500.0
        try:
            payload = await self.get_json(_URL, params=params)
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        features = payload.get("features")
        if not isinstance(features, list):
            return None
        items: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue
            title = _as_text(properties.get("title"))
            if not title:
                continue
            magnitude = _as_float(properties.get("mag"))
            place = _as_text(properties.get("place"))
            magnitude_text = (
                f"магнитуда {magnitude:.1f}" if magnitude is not None else None
            )
            description_parts = [part for part in (place, magnitude_text) if part]
            items.append(
                {
                    "title": title,
                    "url": _as_text(properties.get("url")),
                    "date": _as_date(properties.get("time")),
                    "description": ", ".join(description_parts) or None,
                }
            )
        if not items:
            return None
        return {"items": items, "source": self.name}
