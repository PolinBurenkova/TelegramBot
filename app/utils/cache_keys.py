""""Cache key builders."""
from __future__ import annotations

from datetime import date


def city_key(name: str) -> str:
    return f"city:{name.lower()}"


def weather_key(lat: float, lon: float) -> str:
    return f"weather:{lat:.2f}:{lon:.2f}"


def wiki_key(title: str) -> str:
    return f"wiki:{title.lower()}"


def photo_key(city_id: int) -> str:
    return f"photo:{city_id}"


def geonames_key(query: str) -> str:
    return f"geonames:{query.lower()}"


def leaderboard_key(category: str, page: int) -> str:
    return f"lb:{category}:{page}"


def quota_key(provider: str, day: date | None = None) -> str:
    d = (day or date.today()).isoformat()
    return f"quota:{provider}:{d}"