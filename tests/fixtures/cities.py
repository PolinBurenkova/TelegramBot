# tests/fixtures/cities.py
"""Фабрики тестовых данных городов.

Поля соответствуют реальной модели `app.models.city.City`:
name, normalized_name (unique), country_code, country_name, region,
population, lat, lon, source.
"""

from __future__ import annotations

from typing import Any

from app.models import City
from app.utils.validators import normalize_city

DEFAULT_CITY_NAME = "Москва"


def city_data(name: str = DEFAULT_CITY_NAME, **overrides: Any) -> dict[str, Any]:
    """Данные города; normalized_name по умолчанию считается из name."""
    data: dict[str, Any] = {
        "name": name,
        "normalized_name": normalize_city(name),
        "country_code": "RU",
        "country_name": "Россия",
        "region": "Москва",
        "population": 13_000_000,
        "lat": 55.7558,
        "lon": 37.6173,
        "source": "test",
    }
    data.update(overrides)
    return data


def make_city(name: str = DEFAULT_CITY_NAME, **overrides: Any) -> City:
    """Экземпляр `City` (не сохранённый в БД)."""
    return City(**city_data(name, **overrides))


__all__ = ["DEFAULT_CITY_NAME", "city_data", "make_city"]
