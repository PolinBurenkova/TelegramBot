"""Mapillary response schema."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MapillaryImage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    thumb_1024_url: str | None = None
    geometry: dict | None = None