"""Репозиторий выданных достижений."""

from sqlalchemy import select

from app.models.user_achievement import UserAchievement
from app.repositories.base import BaseRepository


class UserAchievementRepository(BaseRepository[UserAchievement]):
    """Совместимый алиас; канонический класс — ``achievement_repo.UserAchievementRepo``."""

    model = UserAchievement

    async def has(self, user_id: int, achievement_id: int) -> bool:
        result = await self.session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        return result.scalar_one_or_none() is not None