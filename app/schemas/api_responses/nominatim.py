"""Nominatim response schema."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NominatimPlace(BaseModel):
    model_config = ConfigDict(extra="ignore")

    display_name: str | None = None
    lat: str | None = None
    lon: str | None = None
    place_id: int | None = None