# app/models/game.py
"""Игровая сессия «Города+»."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import GameStatus, GameType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.game_move import GameMove
    from app.models.user import User


class Game(TimestampMixin, Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    game_type: Mapped[GameType] = mapped_column(
        Enum(GameType, values_callable=lambda x: [e.value for e in x], name="game_type"),
        default=GameType.CITIES, nullable=False,
    )
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus, values_callable=lambda x: [e.value for e in x], name="game_status"),
        default=GameStatus.ACTIVE, nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moves_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(10), default="easy", nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Совместимость: game_service использует cities_count
    @property
    def cities_count(self) -> int:
        return self.moves_count

    @cities_count.setter
    def cities_count(self, value: int) -> None:
        self.moves_count = int(value)

    user: Mapped["User"] = relationship(back_populates="games")
    moves: Mapped[list["GameMove"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="GameMove.created_at",
    )

    __table_args__ = (
        Index("ix_games_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Game id={self.id} user_id={self.user_id} status={self.status.value}>"