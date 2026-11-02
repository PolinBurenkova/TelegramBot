# app/models/game_move.py
"""Ход в игре «Города+»."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import IdMixin

if TYPE_CHECKING:
    from app.models.game import Game


class GameMove(IdMixin, Base):
    __tablename__ = "game_moves"

    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    city_name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    move_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    is_user: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    game: Mapped["Game"] = relationship(back_populates="moves")

    __table_args__ = (
        UniqueConstraint("game_id", "normalized_name", name="uq_game_city"),
    )

    def __repr__(self) -> str:
        return f"<GameMove game_id={self.game_id} city={self.city_name!r}>"