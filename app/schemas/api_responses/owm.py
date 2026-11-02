"""OpenWeatherMap response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OWMWeather(BaseModel):
    model_config = ConfigDict(extra="ignore")

    main: str | None = None
    description: str | None = None
    icon: str | None = None


class OWMMain(BaseModel):
    model_config = ConfigDict(extra="ignore")

    temp: float = 0.0
    feels_like: float = 0.0
    humidity: int = 0


class OWMWind(BaseModel):
    model_config = ConfigDict(extra="ignore")

    speed: float = 0.0


class OWMResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    main: OWMMain | None = None
    weather: list[OWMWeather] = []
    wind: OWMWind | None = None