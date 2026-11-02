"""User settings."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.schemas.settings import SettingsSchema, SettingsUpdate


class SettingsService:
    """Manage user settings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepo(session)

    async def get(self, user: User) -> SettingsSchema:
        return SettingsSchema(
            locale=user.locale,
            notify=user.notify,
            difficulty=user.difficulty,
            timezone="UTC",
        )

    async def set_difficulty(self, user: User, difficulty: str) -> None:
        """Установить сложность по умолчанию для пользователя."""
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "easy"
        user.difficulty = difficulty
        await self.session.flush()

    async def update(self, user: User, data: SettingsUpdate) -> SettingsSchema:
        if data.locale:
            await self.users.update_locale(user, data.locale)
        if data.notify is not None:
            await self.users.set_notify(user, data.notify)
        return await self.get(user)