"""REST Countries response schema."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RestCountry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: dict | None = None
    cca2: str | None = None
    capital: list[str] = []
    population: int | None = None
    region: str | None = None
    flags: dict | None = Field(default=None)