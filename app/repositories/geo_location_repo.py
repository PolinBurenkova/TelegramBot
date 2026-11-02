"""GeoLocation repository."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.models.geo_location import GeoLocation
from app.repositories.base import BaseRepo


class GeoLocationRepo(BaseRepo[GeoLocation]):
    """GeoLocation DB operations."""

    model = GeoLocation

    async def random_by_difficulty(
        self, difficulty: str, exclude_ids: list[int] | None = None
    ) -> GeoLocation | None:
        """Random location for given difficulty."""
        stmt = select(GeoLocation).where(GeoLocation.difficulty == difficulty)
        if exclude_ids:
            stmt = stmt.where(GeoLocation.id.notin_(exclude_ids))
        stmt = stmt.order_by(func.random()).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_coords(
        self, lat: float, lon: float, source: str
    ) -> GeoLocation | None:
        """Look up by coordinates + source."""
        res = await self.session.execute(
            select(GeoLocation).where(
                GeoLocation.lat == lat,
                GeoLocation.lon == lon,
                GeoLocation.source == source,
            )
        )
        return res.scalar_one_or_none()

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> int:
        """Bulk insert with dedup by coords+source."""
        inserted = 0
        for row in rows:
            exists = await self.get_by_coords(
                row["lat"], row["lon"], row["source"]
            )
            if exists:
                continue
            await self.create(**row)
            inserted += 1
        return inserted


# Совместимость: geo_location_service импортирует GeoLocationRepository
GeoLocationRepository = GeoLocationRepo