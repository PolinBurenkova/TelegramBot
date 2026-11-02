"""Bing Streetside — панорама по координатам. Ключ BING_MAPS_API_KEY.

REST /REST/v1/Imagery/Metadata/Streetside?center={lat},{lon}&radius={м}.
Радиус приходит в градусах (как у kartaview) — переводим в метры.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

_METADATA_URL = "https://dev.virtualearth.net/REST/v1/Imagery/Metadata/Streetside"
#: Верхняя граница радиуса для метаданных Streetside.
_MAX_RADIUS_M = 1_000
#: Градус широты ≈ 111 км.
_METERS_PER_DEGREE = 111_000


class BingStreetsideProvider(BaseProvider):
    """Imagery/Metadata/Streetside: imageUrl первого ресурса."""

    name = "bing_streetside"
    category = "panorama"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """BING_MAPS_API_KEY (Settings) или переменные окружения."""
        secret = get_settings().bing_maps_api_key
        if secret:
            return secret.get_secret_value()
        return provider_key("bing_maps", "bing_streetside")

    async def fetch(
        self, lat: float, lon: float, radius: float = 0.02, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Панорама рядом с точкой или None."""
        key = self.api_key
        if not key:
            return None
        payload = await self.get_json(
            _METADATA_URL,
            params={
                "center": f"{lat},{lon}",
                "radius": _radius_m(radius),
                "key": key,
            },
        )
        image_url = _image_url(payload)
        if not image_url:
            return None
        return {
            "image_url": image_url,
            "lat": lat,
            "lon": lon,
            "source": "bing_streetside",
        }


def _radius_m(radius: float) -> int:
    """Градусы → метры с зажимом в [1, 1000]."""
    if not isinstance(radius, (int, float)) or isinstance(radius, bool):
        return _MAX_RADIUS_M
    meters = int(abs(radius) * _METERS_PER_DEGREE)
    return min(_MAX_RADIUS_M, max(1, meters))


def _image_url(payload: Any) -> str | None:
    """imageUrl первого ресурса из resourceSets."""
    if not isinstance(payload, dict):
        return None
    resource_sets = payload.get("resourceSets")
    if not isinstance(resource_sets, list) or not resource_sets:
        return None
    first_set = resource_sets[0]
    if not isinstance(first_set, dict):
        return None
    resources = first_set.get("resources")
    if not isinstance(resources, list) or not resources:
        return None
    first = resources[0]
    if not isinstance(first, dict):
        return None
    url = first.get("imageUrl")
    return url.strip() if isinstance(url, str) and url.strip() else None
