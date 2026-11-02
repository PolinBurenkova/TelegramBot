# app/models/__init__.py
"""Реэкспорт всех моделей и метаданных.

Импорт этого модуля гарантирует, что все таблицы зарегистрированы
в Base.metadata — это нужно для Alembic autogenerate.
"""

from __future__ import annotations

from app.database import async_session_factory, async_engine, dispose_engine, get_session
from app.models.achievement import Achievement
from app.models.api_cache import ApiCache
from app.models.base import Base
from app.models.city import City
from app.models.daily_challenge import DailyChallenge
from app.models.enums import (
    AchievementCode,
    GameStatus,
    GameType,
    ProviderFunction,
)
from app.models.game import Game
from app.models.game_move import GameMove
from app.models.geo_location import GeoLocation
from app.models.mixins import IdMixin, TimestampMixin
from app.models.notification import Notification
from app.models.profile import Profile
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.models.user_used_city import UserUsedCity

__all__ = [
    "Achievement",
    "AchievementCode",
    "ApiCache",
    "Base",
    "City",
    "DailyChallenge",
    "Game",
    "GameMove",
    "GameStatus",
    "GameType",
    "GeoLocation",
    "IdMixin",
    "Notification",
    "Profile",
    "ProviderFunction",
    "TimestampMixin",
    "User",
    "UserAchievement",
    "UserUsedCity",
    "async_engine",
    "async_session_factory",
    "dispose_engine",
    "get_session",
]