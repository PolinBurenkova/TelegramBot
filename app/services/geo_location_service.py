"""Выбор локации для GeoGuessr."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo_location import GeoLocation
from app.repositories.city_repo import CityRepo
from app.repositories.geo_location_repo import GeoLocationRepository


class GeoLocationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GeoLocationRepository(session)
        self._cities = CityRepo(session)

    async def random(self, difficulty: str = "medium") -> Any | None:
        """Случайная локация: таблица geo_locations, иначе справочник городов.

        Возвращаемое значение имеет атрибуты ``lat``, ``lon``, ``country_code``
        (так их читает хендлер GeoGuessr), поэтому подходит и GeoLocation, и City.
        Ограничений по населению нет: сложность влияет только на очки.
        """
        loc: GeoLocation | None = await self._repo.random_by_difficulty(difficulty)
        if loc is not None:
            return loc

        return await self._cities.random()
