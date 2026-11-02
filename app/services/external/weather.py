"""Агрегатор погодных провайдеров (каскад ``weather``).

Модуль только реэкспортирует классы уже реализованных погодных провайдеров и
собирает их в ``WEATHER_PROVIDERS`` — порядок совпадает с дефолтным каскадом
``app.constants.PROVIDER_CHAINS["weather"]``.

Реализованы и включены: openweather, open_meteo, weather_api, weatherstack,
visual_crossing, tomorrow_io, weatherbit, meteosource, accuweather.
Пустые (0 байт) модули сюда не импортируются — иначе был бы ``ImportError``;
на момент записи таких среди погодных не осталось.

Ключи: у каждого провайдера свой (см. докстринг его модуля).
"""
from __future__ import annotations

from app.services.external.accuweather import AccuweatherProvider
from app.services.external.base import BaseProvider
from app.services.external.meteosource import MeteosourceProvider
from app.services.external.open_meteo import OpenMeteoProvider
from app.services.external.openweather import OpenWeatherProvider
from app.services.external.tomorrow_io import TomorrowIOProvider
from app.services.external.visual_crossing import VisualCrossingProvider
from app.services.external.weather_api import WeatherAPIProvider
from app.services.external.weatherbit import WeatherbitProvider
from app.services.external.weatherstack import WeatherstackProvider

WEATHER_PROVIDERS: tuple[type[BaseProvider], ...] = (
    OpenWeatherProvider,
    OpenMeteoProvider,
    WeatherAPIProvider,
    WeatherstackProvider,
    VisualCrossingProvider,
    TomorrowIOProvider,
    WeatherbitProvider,
    MeteosourceProvider,
    AccuweatherProvider,
)

__all__ = [
    "WEATHER_PROVIDERS",
    "AccuweatherProvider",
    "MeteosourceProvider",
    "OpenMeteoProvider",
    "OpenWeatherProvider",
    "TomorrowIOProvider",
    "VisualCrossingProvider",
    "WeatherAPIProvider",
    "WeatherbitProvider",
    "WeatherstackProvider",
]
