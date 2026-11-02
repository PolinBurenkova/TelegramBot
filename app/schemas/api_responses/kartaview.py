"""KartaView response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KartaViewItem(BaseModel):
    """Одна панорама KartaView."""

    model_config = ConfigDict(extra="ignore")

    lat: str | float | None = None
    lng: str | float | None = None
    thumb_url: str | None = None
    url: str | None = None


class KartaViewResponse(BaseModel):
    """Ответ /2.0/photo/ (два варианта тела)."""

    model_config = ConfigDict(extra="ignore")

    status: dict | None = None
    currentPageItems: list[KartaViewItem] = []
    result: dict | None = None
