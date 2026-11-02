# app/models/achievement.py
"""Справочник достижений."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Achievement(IdMixin, TimestampMixin, Base):
    __tablename__ = "achievements"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)

    users: Mapped[list["User"]] = relationship(
        secondary="user_achievements", back_populates="achievements", viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Achievement code={self.code!r}>"
    