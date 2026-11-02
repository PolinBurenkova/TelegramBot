"""Перечисления, используемые в моделях."""

from __future__ import annotations

from enum import Enum


class GameStatus(str, Enum):
    ACTIVE = "active"
    FINISHED = "finished"
    ABANDONED = "abandoned"
    TIMEOUT = "timeout"


class GameType(str, Enum):
    CITIES = "cities"
    GEOGUESSR = "geoguessr"


class AchievementCode(str, Enum):
    FIRST_GAME = "first_game"
    TEN_GAMES = "ten_games"
    FIFTY_CITIES = "fifty_cities"
    RARE_CITY = "rare_city"
    WIN_10_MOVES = "win_10_moves"
    LEVEL_GEOGRAPHER = "level_geographer"


class ProviderFunction(str, Enum):
    CITIES = "cities"
    WEATHER = "weather"
    PHOTO = "photo"
    MAPS = "maps"
    WIKI = "wiki"
    COUNTRIES = "countries"
    PANORAMA = "panorama"
    TRANSLATE = "translate"
    TIMEZONE = "timezone"
    EXCHANGE = "exchange"
    HOLIDAYS = "holidays"
    AIR_QUALITY = "air_quality"
    POI = "poi"
    NATURE = "nature"
    MEDIA = "media"
    IP_GEO = "ip_geo"