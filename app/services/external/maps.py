"""Агрегатор картографических провайдеров (каскад ``maps``).

Модуль только реэкспортирует классы уже реализованных карт-провайдеров и
собирает их в ``MAP_PROVIDERS`` — порядок совпадает с дефолтным каскадом
``app.constants.PROVIDER_CHAINS["maps"]``.

Реализованы и включены: osm_maps, yandex_maps, mapbox, maptiler, thunderforest,
stadia_maps. Пустые (0 байт) модули сюда не импортируются — иначе был бы
``ImportError``; на момент записи таких среди картографических не осталось.

Ключи: без ключа — osm_maps; у остальных ключ обязателен (см. их модули).
"""
from __future__ import annotations

from app.services.external.base import BaseProvider
from app.services.external.mapbox import MapboxProvider
from app.services.external.maptiler import MapTilerProvider
from app.services.external.osm_maps import OSMStaticMapProvider
from app.services.external.stadia_maps import StadiaMapsProvider
from app.services.external.thunderforest import ThunderForestProvider
from app.services.external.yandex_maps import YandexMapsProvider

MAP_PROVIDERS: tuple[type[BaseProvider], ...] = (
    OSMStaticMapProvider,
    YandexMapsProvider,
    MapboxProvider,
    MapTilerProvider,
    ThunderForestProvider,
    StadiaMapsProvider,
)

__all__ = [
    "MAP_PROVIDERS",
    "MapTilerProvider",
    "MapboxProvider",
    "OSMStaticMapProvider",
    "StadiaMapsProvider",
    "ThunderForestProvider",
    "YandexMapsProvider",
]
