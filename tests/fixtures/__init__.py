# tests/fixtures/__init__.py
"""Фабрики тестовых данных (dict-данные и экземпляры моделей, без сети и БД)."""

from __future__ import annotations

from tests.fixtures.cities import DEFAULT_CITY_NAME, city_data, make_city
from tests.fixtures.games import DEFAULT_GAME_USER_ID, game_data, make_game
from tests.fixtures.geo_locations import (
    DEFAULT_GEO_PANORAMA_URL,
    geo_location_data,
    make_geo_location,
)
from tests.fixtures.users import DEFAULT_USER_TG_ID, make_user, user_data

__all__ = [
    "DEFAULT_CITY_NAME",
    "DEFAULT_GAME_USER_ID",
    "DEFAULT_GEO_PANORAMA_URL",
    "DEFAULT_USER_TG_ID",
    "city_data",
    "game_data",
    "geo_location_data",
    "make_city",
    "make_game",
    "make_geo_location",
    "make_user",
    "user_data",
]
