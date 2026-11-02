"""Panoramax — панорамы по координатам. Ключ не нужен.

STAC /search по bbox вокруг точки (settings.panoramax_base_url = …/api).
Ссылки на картинки берутся из assets фичи (hd/sd/thumb).
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class PanoramaxProvider(BaseProvider):
    """api.panoramax.xyz/api/search: bbox + limit=1."""

    name = "panoramax"
    category = "panorama"
    requires_key = False

    async def fetch(
        self, lat: float, lon: float, radius: float = 0.02, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Панорама рядом с точкой или None."""
        base = get_settings().panoramax_base_url.rstrip("/")
        bbox = f"{lon - radius},{lat - radius},{lon + radius},{lat + radius}"
        payload = await self.get_json(
            f"{base}/search",
            params={"bbox": bbox, "limit": 1},
        )
        feature = _first_feature(payload)
        if feature is None:
            return None
        image_url, thumb_url = _picture_urls(feature)
        if not image_url:
            return None
        pano_lon, pano_lat = _coordinates(feature, lat=lat, lon=lon)
        return {
            "image_url": image_url,
            "thumb_url": thumb_url or image_url,
            "lat": pano_lat,
            "lon": pano_lon,
            "source": "panoramax",
        }


def _first_feature(payload: Any) -> dict[str, Any] | None:
    """Первая фича STAC FeatureCollection."""
    if not isinstance(payload, dict):
        return None
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        return None
    first = features[0]
    return first if isinstance(first, dict) else None


def _picture_urls(feature: dict[str, Any]) -> tuple[str | None, str | None]:
    """(image_url, thumb_url) из assets фичи."""
    assets = feature.get("assets")
    assets = assets if isinstance(assets, dict) else {}
    image = (
        _href(assets.get("hd"))
        or _href(assets.get("sd"))
        or _href(assets.get("visual"))
        or _href(assets.get("thumb"))
    )
    thumb = _href(assets.get("thumb")) or _href(assets.get("thumbnail")) or image
    return image, thumb


def _href(asset: Any) -> str | None:
    """asset.href (или asset.url) как непустая строка."""
    if not isinstance(asset, dict):
        return None
    for field in ("href", "url"):
        value = asset.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _coordinates(
    feature: dict[str, Any], *, lat: float, lon: float
) -> tuple[float, float]:
    """(lon, lat) панорамы; при отсутствии геометрии — координаты запроса."""
    geometry = feature.get("geometry")
    geometry = geometry if isinstance(geometry, dict) else {}
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        return float(lon), float(lat)
    pano_lon, pano_lat = coords[0], coords[1]
    if isinstance(pano_lon, (int, float)) and isinstance(pano_lat, (int, float)):
        return float(pano_lon), float(pano_lat)
    return float(lon), float(lat)
