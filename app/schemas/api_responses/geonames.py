"""GeoNames response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GeoNamesCity(BaseModel):
    """Single GeoNames result."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    country_name: str | None = Field(default=None, alias="countryName")
    country_code: str | None = Field(default=None, alias="countryCode")
    population: int | None = None
    lat: str | None = None
    lng: str | None = None
    geoname_id: int | None = Field(default=None, alias="geonameId")
    timezone: dict | None = None


class GeoNamesResponse(BaseModel):
    """GeoNames searchJSON response."""

    model_config = ConfigDict(extra="ignore")

    total_results_count: int | None = Field(default=None, alias="totalResultsCount")
    geonames: list[GeoNamesCity] = Field(default_factory=list)
    status: dict | None = None