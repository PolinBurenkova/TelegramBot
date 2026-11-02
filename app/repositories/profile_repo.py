"""Profile repository."""
from __future__ import annotations

from sqlalchemy import select

from app.models.profile import Profile
from app.repositories.base import BaseRepo


class ProfileRepo(BaseRepo[Profile]):
    """Profile DB operations."""

    model = Profile

    async def get_by_user(self, user_id: int) -> Profile | None:
        """Find profile by user_id."""
        res = await self.session.execute(select(Profile).where(Profile.user_id == user_id))
        return res.scalar_one_or_none()

    async def add_xp(self, profile: Profile, xp: int) -> None:
        """Increase XP."""
        profile.xp += xp
        await self.session.flush()

    async def increment(self, profile: Profile, field: str, value: int) -> None:
        """Increment integer field."""
        setattr(profile, field, getattr(profile, field) + value)
        await self.session.flush()

    async def reset(self, profile: Profile) -> None:
        """Reset all progress fields."""
        profile.level = 1
        profile.xp = 0
        profile.total_games = 0
        profile.total_wins = 0
        profile.cities_score = 0
        profile.geo_score = 0
        profile.streak_days = 0
        profile.last_played_at = None
        await self.session.flush()


# Совместимость: geo_game_service импортирует ProfileRepository
ProfileRepository = ProfileRepo