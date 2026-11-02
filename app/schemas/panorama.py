"""Panorama schemas."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class PanoramaOut(BaseSchema):
    """Panorama URL + source."""

    url: str
    source: str
    location_id: int | None = None