"""Схемы стран."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class CountryOut(BaseSchema):
    """Страна (REST Countries / FlagCDN)."""

    code: str
    name: str
    capital: str | None = None
    population: int | None = None
    region: str | None = None
    flag_url: str | None = None
