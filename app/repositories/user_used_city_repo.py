"""UserUsedCity repository."""
from __future__ import annotations

from sqlalchemy import delete, select

from app.models.user_used_city import UserUsedCity
from app.repositories.base import BaseRepo


class UserUsedCityRepo(BaseRepo[UserUsedCity]):
    """UserUsedCity DB operations."""

    model = UserUsedCity

    async def add(
        self, user_id: int, city_norm: str, game_id: int | None = None
    ) -> UserUsedCity:
        """Track used city."""
        return await self.create(
            user_id=user_id, city_norm=city_norm, game_id=game_id
        )

    async def exists(
        self, user_id: int, city_norm: str, game_id: int | None = None
    ) -> bool:
        """Was city used in this game (or ever if game_id None)?"""
        stmt = select(UserUsedCity).where(
            UserUsedCity.user_id == user_id,
            UserUsedCity.city_norm == city_norm,
        )
        if game_id is not None:
            stmt = stmt.where(UserUsedCity.game_id == game_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def list_by_game(self, game_id: int) -> list[str]:
        """City norms used in game."""
        res = await self.session.execute(
            select(UserUsedCity.city_norm).where(
                UserUsedCity.game_id == game_id
            )
        )
        return list(res.scalars().all())

    async def list_by_user(self, user_id: int) -> list[str]:
        """All city norms ever used by user."""
        res = await self.session.execute(
            select(UserUsedCity.city_norm).where(
                UserUsedCity.user_id == user_id
            )
        )
        return list(res.scalars().all())

    async def clear_for_user(self, user_id: int) -> int:
        """Delete all user's used cities."""
        result = await self.session.execute(
            delete(UserUsedCity).where(UserUsedCity.user_id == user_id)
        )
        await self.session.flush()
        return int(result.rowcount or 0)