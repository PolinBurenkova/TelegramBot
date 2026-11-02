"""Points calculation."""
from __future__ import annotations

from app.constants import (
    CITY_BASE_POINTS,
    CITY_DIFFICULTY_MULTIPLIER,
    CITY_LENGTH_BONUS_PER_CHAR,
    GEO_MAX_POINTS_PER_ROUND,
    GEO_SCALE_KM,
    WIN_BONUS,
)
from app.utils.geo import haversine_km


class ScoreService:
    """Scoring rules."""

    @staticmethod
    def city_points(city_name: str, difficulty: str = "easy", time_spent: float = 0.0) -> int:
        base = CITY_BASE_POINTS
        length_bonus = max(0, len(city_name) - 4) * CITY_LENGTH_BONUS_PER_CHAR
        mult = CITY_DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)
        return int((base + length_bonus) * mult)

    @staticmethod
    def win_bonus() -> int:
        return WIN_BONUS

    @staticmethod
    def geo_points(distance_km: float, max_points: int = GEO_MAX_POINTS_PER_ROUND) -> int:
        """Exponential decay score for GeoGuessr."""
        import math
        score = max_points * math.exp(-distance_km / GEO_SCALE_KM)
        return max(0, min(max_points, int(score)))

    @staticmethod
    def geo_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_km(lat1, lon1, lat2, lon2)