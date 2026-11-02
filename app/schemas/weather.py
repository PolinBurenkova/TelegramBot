"""Схема погоды."""

from pydantic import BaseModel


class WeatherDTO(BaseModel):
    temp: float | None = None
    feels_like: float | None = None
    description: str | None = None
    icon: str | None = None
    humidity: int | None = None
    wind: float | None = None


# Совместимое имя (schemas/__init__)
WeatherOut = WeatherDTO