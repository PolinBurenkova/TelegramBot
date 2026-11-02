"""Open-Meteo response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OpenMeteoCurrent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    temperature_2m: float | None = None
    wind_speed_10m: float | None = None
    weather_code: int | None = None


class OpenMeteoResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float | None = None
    longitude: float | None = None
    current: OpenMeteoCurrent | None = None