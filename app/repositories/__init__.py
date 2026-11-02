"""Repositories — data access layer."""
from __future__ import annotations

from app.repositories.achievement_repo import AchievementRepo, UserAchievementRepo
from app.repositories.api_cache_repo import ApiCacheRepo
from app.repositories.base import BaseRepo
from app.repositories.city_repo import CityRepo
from app.repositories.game_repo import GameRepo, MoveRepo
from app.repositories.geo_location_repo import GeoLocationRepo
from app.repositories.profile_repo import ProfileRepo
from app.repositories.stats_repo import StatsRepo
from app.repositories.user_repo import UserRepo
from app.repositories.user_used_city_repo import UserUsedCityRepo

__all__ = [
    "BaseRepo",
    "UserRepo",
    "ProfileRepo",
    "CityRepo",
    "GameRepo",
    "MoveRepo",
    "GeoLocationRepo",
    "AchievementRepo",
    "UserAchievementRepo",
    "ApiCacheRepo",
    "UserUsedCityRepo",
    "StatsRepo",
]