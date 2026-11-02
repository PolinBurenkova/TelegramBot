# app/models/user_used_city.py
"""Города, уже использованные пользователем (антиповтор)."""

from __future__ import annotations

from datetime import datetime

import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin


class UserUsedCity(IdMixin, Base):
    __tablename__ = "user_used_cities"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    city_norm: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    game_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=True,
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "city_norm", "game_id", name="uq_user_used_city"),
    )