"""Очки GeoGuessr."""

import math

from app.constants import GEO_DECAY_KM, GEO_MAX_SCORE


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние в км между двумя точками."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def calculate_score(distance_km: float, max_score: int = GEO_MAX_SCORE) -> int:
    """Очки: 5000 * exp(-distance/2000)."""
    return int(max_score * math.exp(-distance_km / GEO_DECAY_KM))