# tests/fixtures/geo_locations.py
"""Фабрики тестовых данных точек для GeoGuessr.

Поля соответствуют реальной модели `app.models.geo_location.GeoLocation`:
image_url, thumb_url, lat, lon, country_code, difficulty, source.
"""

from __future__ import annotations

from typing import Any

from app.models import GeoLocation

DEFAULT_GEO_PANORAMA_URL = "https://example.test/panorama.jpg"


def geo_location_data(**overrides: Any) -> dict[str, Any]:
    """Данные точки для `GeoLocation(**geo_location_data())`."""
    data: dict[str, Any] = {
        "image_url": DEFAULT_GEO_PANORAMA_URL,
        "thumb_url": "https://example.test/panorama_thumb.jpg",
        "lat": 55.7558,
        "lon": 37.6173,
        "country_code": "RU",
        "difficulty": "medium",
        "source": "test",
    }
    data.update(overrides)
    return data


def make_geo_location(**overrides: Any) -> GeoLocation:
    """Экземпляр `GeoLocation` (не сохранённый в БД)."""
    return GeoLocation(**geo_location_data(**overrides))


__all__ = ["DEFAULT_GEO_PANORAMA_URL", "geo_location_data", "make_geo_location"]
