# app/models/user.py
"""Пользователь Telegram."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.achievement import Achievement
    from app.models.game import Game
    from app.models.profile import Profile


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True,
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="ru", nullable=False)
    show_weather: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_photo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locale: Mapped[str] = mapped_column(String(2), default="ru", nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(10), default="easy", nullable=False)
    notify: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    profile: Mapped["Profile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan",
    )
    games: Mapped[list["Game"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )
    achievements: Mapped[list["Achievement"]] = relationship(
        secondary="user_achievements", back_populates="users", viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.tg_id} level={self.level}>"