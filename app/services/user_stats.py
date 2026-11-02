"""Статистика пользователя для /profile."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.profile_repo import ProfileRepo
from app.utils.xp import level_from_xp


class UserStats:
    """Агрегированная статистика по профилю."""

    def __init__(self, session: AsyncSession) -> None:
        self._profiles = ProfileRepo(session)

    async def get(self, user_id: int) -> dict[str, Any]:
        profile = await self._profiles.get_by_user(user_id)
        if profile is None:
            return {
                "level": 1,
                "xp": 0,
                "games": 0,
                "cities_used": 0,
                "countries_visited": 0,
            }
        level, _, _ = level_from_xp(profile.xp)
        return {
            "level": level,
            "xp": profile.xp,
            "games": profile.games_played,
            "cities_used": profile.cities_named,
            "countries_visited": 0,
        }
