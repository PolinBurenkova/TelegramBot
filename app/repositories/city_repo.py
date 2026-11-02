"""City repository."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.models.city import City
from app.repositories.base import BaseRepo


class CityRepo(BaseRepo[City]):
    """City DB operations."""

    model = City

    async def get_by_name(self, name: str, locale: str = "ru") -> City | None:
        """Look up city by normalized name."""
        from app.utils.validators import normalize_city

        norm = normalize_city(name)
        res = await self.session.execute(
            select(City).where(City.normalized_name == norm)
        )
        return res.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> list[City]:
        """Prefix search on name_norm."""
        q = query.strip().lower()
        res = await self.session.execute(
            select(City)
            .where(City.normalized_name.like(f"{q}%"))
            .order_by(City.population.desc().nullslast())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def list_starting_with(self, letter: str, limit: int = 200) -> list[City]:
        """Cities starting with letter (for bot reply)."""
        res = await self.session.execute(
            select(City)
            .where(City.normalized_name.like(f"{letter.lower()}%"))
            .limit(limit)
        )
        return list(res.scalars().all())

    async def random(
        self,
        country_code: str | None = None,
        min_population: int | None = None,
    ) -> City | None:
        """Random city (optional filters)."""
        stmt = select(City)
        if country_code:
            stmt = stmt.where(City.country_code == country_code)
        if min_population:
            stmt = stmt.where(City.population >= min_population)
        stmt = stmt.order_by(func.random()).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_from_geonames(self, data: dict[str, Any]) -> City:
        """Insert city from normalized provider dict (GeoNames/Nominatim)."""
        from app.utils.validators import normalize_city

        name = data.get("name", "")
        lat = data.get("lat")
        lon = data.get("lon") if data.get("lon") is not None else data.get("lng")
        return await self.create(
            name=name,
            normalized_name=normalize_city(name),
            country_code=(data.get("country_code") or "XX")[:2].upper(),
            country_name=data.get("country_name") or "",
            population=int(data.get("population") or 0),
            lat=float(lat) if lat is not None else 0.0,
            lon=float(lon) if lon is not None else 0.0,
            source=str(data.get("source") or "geonames")[:20],
        )

    async def bulk_insert(self, cities: list[dict[str, Any]]) -> int:
        """Bulk insert (ignoring duplicates by name_norm)."""
        if not cities:
            return 0
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        # Portable approach: per-row try/except
        inserted = 0
        for row in cities:
            exists = await self.get_by_name(row["name"])
            if exists:
                continue
            try:
                await self.create(**row)
                inserted += 1
            except Exception:
                continue
        return inserted


# Совместимость: city_service импортирует CityRepository
CityRepository = CityRepo