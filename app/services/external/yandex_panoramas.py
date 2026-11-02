"""Yandex Panoramas — панорама по координатам. Публичный API, ключ не нужен.

Endpoint https://api-maps.yandex.ru/services/panoramas/1.x/ используется
JS API карт и работает без ключа, поэтому requires_key = False. Если задан
YANDEX_MAPS_API_KEY / YANDEX_PANORAMAS_API_KEY, он добавляется как apikey —
это не обязательно, но может влиять на лимиты.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

_API_URL = "https://api-maps.yandex.ru/services/panoramas/1.x/"


class YandexPanoramasProvider(BaseProvider):
    """services/panoramas/1.x?ll=lon,lat&l=stv&format=json."""

    name = "yandex_panoramas"
    category = "panorama"
    requires_key = False

    @property
    def api_key(self) -> str | None:
        """Необязательный ключ: Settings → переменные окружения."""
        secret = get_settings().yandex_panoramas_api_key
        if secret:
            return secret.get_secret_value()
        return provider_key("yandex_panoramas", "yandex_maps")

    async def fetch(
        self, lat: float, lon: float, radius: float = 0.02, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Панорама рядом с точкой или None."""
        params: dict[str, Any] = {
            "ll": f"{lon},{lat}",
            "l": "stv",
            "lang": "ru_RU",
            "format": "json",
        }
        key = self.api_key
        if key:
            params["apikey"] = key
        payload = await self.get_json(_API_URL, params=params)
        return _panorama(payload, lat=lat, lon=lon)


def _panorama(
    payload: Any, *, lat: float, lon: float
) -> dict[str, Any] | None:
    """Первая панорама из data.data."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    data = data if isinstance(data, dict) else {}
    items = data.get("data")
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    if not isinstance(first, dict):
        return None
    images = first.get("Images")
    images = images if isinstance(images, dict) else {}
    url = images.get("imageUrl") or images.get("thumbUrl")
    if not isinstance(url, str) or not url.strip():
        return None
    pano_lon, pano_lat = _coordinates(first, lat=lat, lon=lon)
    return {
        "image_url": url.strip(),
        "lat": pano_lat,
        "lon": pano_lon,
        "source": "yandex_panoramas",
    }


def _coordinates(
    item: dict[str, Any], *, lat: float, lon: float
) -> tuple[float, float]:
    """(lon, lat) панорамы; при отсутствии Coordinates — координаты запроса."""
    coords = item.get("Coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        return float(lon), float(lat)
    pano_lon, pano_lat = coords[0], coords[1]
    if isinstance(pano_lon, (int, float)) and isinstance(pano_lat, (int, float)):
        return float(pano_lon), float(pano_lat)
    return float(lon), float(lat)
