# app/models/daily_challenge.py
"""Ежедневное задание."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class DailyChallenge(IdMixin, TimestampMixin, Base):
    __tablename__ = "daily_challenges"

    challenge_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    city_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hint: Mapped[str] = mapped_column(String(255), nullable=False)
    reward_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    __table_args__ = (
        UniqueConstraint("challenge_date", name="uq_daily_challenge_date"),
    )