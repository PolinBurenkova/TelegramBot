"""Wikipedia response schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WikiPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pageid: int | None = None
    title: str | None = None
    extract: str | None = None
    missing: str | None = None
    original: dict | None = None


class WikiQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pages: dict[str, WikiPage] = {}


class WikiExtract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: WikiQuery | None = None