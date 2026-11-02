"""Схема города."""
from __future__ import annotations

from pydantic import BaseModel


class CityIn(BaseModel):
    """Ввод названия города."""

    name: str


class CityDTO(BaseModel):
    geonames_id: int | None = None
    name: str
    name_ru: str | None = None
    country: str | None = None
    country_code: str | None = None
    lat: float | None = None
    lon: float | None = None
    population: int | None = None
    timezone: str | None = None


# Совместимое имя для API-ответов (schemas/__init__)
CityOut = CityDTO