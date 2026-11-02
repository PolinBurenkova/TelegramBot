# app/models/profile.py
"""Профиль пользователя (1:1 с User)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Profile(IdMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    games_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    games_won: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cities_named: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_letter: Mapped[str | None] = mapped_column(String(2), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cities_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    geo_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_played_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Совместимость: сервисы и хендлеры используют total_* имена
    @property
    def total_games(self) -> int:
        return self.games_played

    @total_games.setter
    def total_games(self, value: int) -> None:
        self.games_played = int(value)

    @property
    def total_wins(self) -> int:
        return self.games_won

    @total_wins.setter
    def total_wins(self, value: int) -> None:
        self.games_won = int(value)

    user: Mapped["User"] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile user_id={self.user_id} games={self.games_played}>"