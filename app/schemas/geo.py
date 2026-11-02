"""Схемы GeoGuessr."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class GeoLocationOut(BaseSchema):
    """Точка GeoGuessr."""

    id: int | None = None
    lat: float
    lon: float
    country_code: str | None = None
    image_url: str | None = None


class GeoGuessResult(BaseSchema):
    """Результат попытки."""

    distance_km: float
    score: int
    real_lat: float
    real_lon: float
    guess_lat: float
    guess_lon: float
