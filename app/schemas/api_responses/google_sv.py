"""Схемы ответа Google Street View (metadata и static image)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GoogleSVLocation(BaseModel):
    """Координаты панорамы."""

    model_config = ConfigDict(extra="ignore")

    lat: float | None = None
    lng: float | None = None


class GoogleSVMetadata(BaseModel):
    """Ответ /streetview/metadata: status + pano_id + location."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: str = ""
    pano_id: str | None = Field(default=None, alias="pano_id")
    location: GoogleSVLocation | None = None
    date: str | None = None
    copyright: str | None = None

    @property
    def is_ok(self) -> bool:
        """Метаданные пригодны: Google вернул OK и есть панорама."""
        return self.status == "OK" and bool(self.pano_id)
