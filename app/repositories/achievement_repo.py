"""Achievement repositories."""
from __future__ import annotations

from sqlalchemy import select

from app.models.achievement import Achievement
from app.models.user_achievement import UserAchievement
from app.repositories.base import BaseRepo


class AchievementRepo(BaseRepo[Achievement]):
    """Achievement DB operations."""

    model = Achievement

    async def get_by_code(self, code: str) -> Achievement | None:
        """Find by code."""
        res = await self.session.execute(
            select(Achievement).where(Achievement.code == code)
        )
        return res.scalar_one_or_none()

    async def list_all(self) -> list[Achievement]:
        """All achievements."""
        res = await self.session.execute(
            select(Achievement).order_by(Achievement.id)
        )
        return list(res.scalars().all())

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Insert or update by code."""
        updated = 0
        for row in rows:
            existing = await self.get_by_code(row["code"])
            if existing:
                for k, v in row.items():
                    if k != "code":
                        setattr(existing, k, v)
                updated += 1
            else:
                await self.create(**row)
                updated += 1
        return updated


class UserAchievementRepo(BaseRepo[UserAchievement]):
    """UserAchievement DB operations."""

    model = UserAchievement

    async def exists(self, user_id: int, achievement_id: int) -> bool:
        """Check if unlocked."""
        res = await self.session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        return res.scalar_one_or_none() is not None

    async def unlock(self, user_id: int, achievement_id: int) -> bool:
        """Unlock if not already (idempotent)."""
        if await self.exists(user_id, achievement_id):
            return False
        await self.create(user_id=user_id, achievement_id=achievement_id)
        return True

    async def list_by_user(self, user_id: int) -> list[UserAchievement]:
        """All unlocked for user."""
        res = await self.session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        return list(res.scalars().all())

    async def unlocked_ids(self, user_id: int) -> set[int]:
        """IDs of unlocked achievements."""
        res = await self.session.execute(
            select(UserAchievement.achievement_id).where(
                UserAchievement.user_id == user_id
            )
        )
        return set(res.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """Count unlocked."""
        res = await self.session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        return len(list(res.scalars().all()))