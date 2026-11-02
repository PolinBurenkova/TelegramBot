# app/models/mixins.py
"""Общие миксины: id, created_at, updated_at."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column


class IdMixin:
    """Первичный ключ BIGSERIAL.

    В SQLite BIGINT PRIMARY KEY не является алиасом rowid и не автоинкрементится,
    поэтому там тип подменяется на INTEGER (with_variant) — иначе INSERT без id
    падает с «NOT NULL constraint failed».
    """

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )


class TimestampMixin:
    """created_at / updated_at с server-side defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )