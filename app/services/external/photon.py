"""Photon (Komoot, на базе OSM) — поиск городов. Ключ не нужен."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
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


class PhotonProvider(BaseProvider):
    """Photon API Komoot поверх данных OpenStreetMap, регистрация не нужна."""

    name = "photon"
    category = "cities"
    requires_key = False
    base_url = "https://photon.komoot.io"

    async def fetch(self, query: str, **kwargs: Any) -> dict[str, Any] | None:
        base = (get_settings().photon_url or self.base_url).rstrip("/")
        payload = await self.get_json(
            f"{base}/api",
            params={"q": query, "limit": 1, "lang": "ru"},
        )
        if not isinstance(payload, dict):
            return None
        features = payload.get("features") or []
        if not isinstance(features, list) or not features:
            return None
        feature = features[0]
        if not isinstance(feature, dict):
            return None
        geometry = feature.get("geometry")
        coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(coords, list) or len(coords) < 2:
            return None
        lon = _to_float(coords[0])
        lat = _to_float(coords[1])
        if lat is None or lon is None:
            return None
        props = feature.get("properties")
        if not isinstance(props, dict):
            props = {}
        name = props.get("name") or props.get("city") or props.get("street") or query
        return {
            "geonames_id": _to_int(props.get("osm_id")),
            "name": name,
            "name_ru": name,
            "country_code": _upper(props.get("countrycode")),
            "country_name": props.get("country"),
            "lat": lat,
            "lon": lon,
            "population": None,
            "timezone": None,
            "source": self.name,
        }
