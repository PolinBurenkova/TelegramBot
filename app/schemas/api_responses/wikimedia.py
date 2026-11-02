"""Wikimedia Commons response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WikimediaImageInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    thumburl: str | None = None
    url: str | None = None


class WikimediaPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    imageinfo: list[WikimediaImageInfo] = []


class WikimediaQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pages: dict[str, WikimediaPage] = {}


class WikimediaResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: WikimediaQuery | None = None
