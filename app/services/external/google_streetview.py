"""Google Street View — панорама по координатам. Ключ GOOGLE_MAPS_API_KEY.

Сначала /streetview/metadata: если status != "OK" панорамы рядом нет → None.
Радиус приходит в градусах (как у kartaview), Google ждёт метры — переводим
и зажимаем в допустимые 50 м. Ключ обязателен и попадает в возвращаемый
image_url (так работает Static Street View), поэтому результат не логируем.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

_METADATA_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
_IMAGE_URL = "https://maps.googleapis.com/maps/api/streetview"
#: Google принимает radius не больше 50 метров.
_MAX_RADIUS_M = 50
#: Градус широты ≈ 111 км.
_METERS_PER_DEGREE = 111_000
_IMAGE_SIZE = "640x400"


class GoogleStreetViewProvider(BaseProvider):
    """metadata + static streetview: проверка наличия и URL картинки."""

    name = "google_streetview"
    category = "panorama"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """GOOGLE_STREETVIEW_API_KEY (Settings) или переменные окружения."""
        secret = get_settings().google_streetview_api_key
        if secret:
            return secret.get_secret_value()
        return provider_key("google_streetview", "google_maps")

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
                "location": f"{lat},{lon}",
                "radius": _radius_m(radius),
                "key": key,
            },
        )
        if not isinstance(payload, dict) or payload.get("status") != "OK":
            return None
        location = payload.get("location")
        location = location if isinstance(location, dict) else {}
        pano_lat = _as_float(location.get("lat"), lat)
        pano_lon = _as_float(location.get("lng"), lon)
        image_url = (
            f"{_IMAGE_URL}?size={_IMAGE_SIZE}"
            f"&location={pano_lat},{pano_lon}&key={key}"
        )
        return {
            "image_url": image_url,
            "lat": pano_lat,
            "lon": pano_lon,
            "source": "google_streetview",
        }


def _radius_m(radius: float) -> int:
    """Градусы → метры с зажимом в [1, 50]."""
    if not isinstance(radius, (int, float)) or isinstance(radius, bool):
        return _MAX_RADIUS_M
    meters = int(abs(radius) * _METERS_PER_DEGREE)
    return min(_MAX_RADIUS_M, max(1, meters))


def _as_float(value: Any, default: float) -> float:
    """float(value) или default, если значение не число."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return float(default)
