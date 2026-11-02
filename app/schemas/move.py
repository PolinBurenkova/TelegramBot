"""Move input schemas."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class MoveIn(BaseSchema):
    """User move input."""

    city_name: str