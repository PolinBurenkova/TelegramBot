"""Achievements."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACHIEVEMENTS
from app.models.achievement import Achievement
from app.models.user import User
from app.repositories.achievement_repo import AchievementRepo, UserAchievementRepo


class AchievementService:
    """Seeding + unlocking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ach = AchievementRepo(session)
        self.user_ach = UserAchievementRepo(session)

    async def seed(self) -> None:
        """Ensure default achievements exist."""
        for code, meta in ACHIEVEMENTS.items():
            existing = await self.ach.get_by_code(code)
            if existing:
                continue
            await self.ach.create(
                code=code,
                title=meta["title"],
                description=meta["desc"],
                icon=meta["title"][:2],
            )

    async def unlock(self, user: User, code: str) -> bool:
        ach = await self.ach.get_by_code(code)
        if not ach:
            return False
        return await self.user_ach.unlock(user.id, ach.id)

    async def list_for_user(self, user: User) -> list[tuple[Achievement, bool]]:
        all_ach = await self.ach.list_all()
        unlocked = await self.user_ach.unlocked_ids(user.id)
        return [(a, a.id in unlocked) for a in all_ach]