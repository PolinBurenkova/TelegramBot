"""Geo helpers."""
from __future__ import annotations

import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def format_distance(km: float) -> str:
    """Pretty distance string."""
    if km < 1:
        return f"{int(km * 1000)} м"
    if km < 100:
        return f"{km:.1f} км"
    return f"{int(km)} км"


def format_coordinates(lat: float, lon: float) -> str:
    """'55.7500, 37.6100'."""
    return f"{lat:.4f}, {lon:.4f}"