"""Схемы достижений."""
from __future__ import annotations

from datetime import datetime

from app.schemas.common import BaseSchema


class AchievementOut(BaseSchema):
    """Достижение справочника."""

    code: str
    title: str
    description: str
    icon: str


class UserAchievementOut(BaseSchema):
    """Достижение пользователя."""

    user_id: int
    achievement: AchievementOut
    unlocked_at: datetime | None = None
