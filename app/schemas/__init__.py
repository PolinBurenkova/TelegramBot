"""Pydantic schemas."""
from __future__ import annotations

from app.schemas.achievement import AchievementOut, UserAchievementOut
from app.schemas.city import CityIn, CityOut
from app.schemas.common import OkResponse, Page, Pagination
from app.schemas.country import CountryOut
from app.schemas.game import GameMoveOut, GameOut, MoveResult
from app.schemas.geo import GeoGuessResult, GeoLocationOut
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardPage
from app.schemas.move import MoveIn
from app.schemas.panorama import PanoramaOut
from app.schemas.profile import ProfileOut, ProfileView
from app.schemas.settings import SettingsSchema, SettingsUpdate
from app.schemas.user import UserCreate, UserOut
from app.schemas.weather import WeatherOut

__all__ = [
    "Pagination", "Page", "OkResponse",
    "UserOut", "UserCreate",
    "ProfileOut", "ProfileView",
    "CityIn", "CityOut",
    "CountryOut",
    "WeatherOut",
    "GameOut", "GameMoveOut", "MoveResult", "MoveIn",
    "GeoLocationOut", "GeoGuessResult",
    "AchievementOut", "UserAchievementOut",
    "LeaderboardEntry", "LeaderboardPage",
    "SettingsSchema", "SettingsUpdate",
    "PanoramaOut",
]