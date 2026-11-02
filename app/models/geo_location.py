
"""Точки для GeoGuessr (панорамы)."""

from __future__ import annotations

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class GeoLocation(IdMixin, TimestampMixin, Base):
    __tablename__ = "geo_locations"

    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumb_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_geo_locations_source_country", "source", "country_code"),
    )