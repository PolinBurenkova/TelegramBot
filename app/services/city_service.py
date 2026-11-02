"""Сервис городов.

Поиск: локальная БД → внешний геокодер (GeoNames, затем Nominatim).
Найденный извне город сохраняется в справочник. find() возвращает модель
City (для игровых сервисов), get_or_raise() — словарь с координатами.
"""
from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_TTL_CITY
from app.exceptions import CityNotFound
from app.models.city import City
from app.repositories.city_repo import CityRepo
from app.schemas.city import CityDTO
from app.services.external.geonames import GeoNamesProvider
from app.services.external.nominatim import NominatimProvider
from app.utils.cache import get_cache
from app.utils.cache_keys import geonames_key


class CityService:
    """Поиск, валидация и DTO городов."""

    def __init__(
        self,
        session: AsyncSession,
        external: Any | None = None,
    ) -> None:
        self._session = session
        self.repo = CityRepo(session)
        self._geonames = GeoNamesProvider()
        self._nominatim = NominatimProvider()
        self._cache = get_cache()
        self._external = external  # зарезервировано для каскадов реестра

    async def find(self, name: str) -> City | None:
        """Ищет город: БД → внешний геокодер (с созданием записи)."""
        normalized = name.strip()
        if not normalized:
            return None

        local = await self.repo.get_by_name(normalized)
        if local is not None:
            return local

        data = await self._fetch_external(normalized)
        if not data:
            return None

        try:
            return await self.repo.create_from_geonames(data)
        except Exception:
            # конкурентная вставка/дубликат — берём существующую запись
            return await self.repo.get_by_name(normalized)

    async def get_or_raise(self, name: str) -> dict[str, Any]:
        """Словарь с координатами города (для GeoGuessr)."""
        city = await self.find(name)
        if city is None:
            raise CityNotFound(f"Город «{name}» не найден")
        return self._city_to_dict(city)

    async def random(self, min_population: int | None = None) -> City | None:
        """Случайный город справочника (стартовый ход бота).

        По умолчанию ограничений по населению нет; параметр сохранён для
        явных выборок (например, «только крупные города»).
        """
        return await self.repo.random(min_population=min_population)

    def to_out(self, city: City) -> CityDTO:
        """Модель → DTO для игровых сервисов."""
        return CityDTO(
            geonames_id=None,
            name=city.name,
            country=city.country_name,
            country_code=city.country_code,
            lat=city.lat,
            lon=city.lon,
            population=city.population,
        )

    async def _fetch_external(self, name: str) -> dict[str, Any] | None:
        """Геокодеры по порядку: GeoNames (если настроен) → Nominatim."""
        cache_key = geonames_key(name)
        try:
            cached = await self._cache.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return cached

        data: dict[str, Any] | None = None
        source = "external"
        for provider in (self._geonames, self._nominatim):
            if not provider.is_configured:
                continue
            try:
                data = await provider.call("search", query=name)
            except Exception as exc:
                logger.warning(
                    "geocoder {} failed for {}: {}", provider.name, name, exc
                )
                data = None
            if data:
                source = provider.name
                break

        if data:
            data.setdefault("source", source)
            try:
                await self._cache.set(cache_key, data, ttl=CACHE_TTL_CITY)
            except Exception:
                pass
        return data

    @staticmethod
    def _city_to_dict(city: City) -> dict[str, Any]:
        return {
            "geonames_id": None,
            "name": city.name,
            "name_ru": city.name,
            "country_code": city.country_code,
            "country_name": city.country_name,
            "lat": city.lat,
            "lon": city.lon,
            "population": city.population,
            "timezone": None,
        }
