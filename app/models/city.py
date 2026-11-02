
"""Справочник городов (из GeoNames / Nominatim / ручных сидов)."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class City(IdMixin, TimestampMixin, Base):
    __tablename__ = "cities"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    population: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)

    @property
    def name_norm(self) -> str:
        """Совместимость: нормализованное имя (game_service и др.)."""
        return self.normalized_name

    def __repr__(self) -> str:
        return f"<City {self.name!r} ({self.country_code}) pop={self.population}>"