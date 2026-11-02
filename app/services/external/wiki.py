"""Википедия (REST API) — краткое описание города. Ключ не нужен."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app.config import get_settings
from app.services.external.base import BaseProvider


class WikiProvider(BaseProvider):
    """REST v1 /page/summary/{title}."""

    name = "wiki"
    category = "wiki"
    requires_key = False

    async def fetch(self, title: str, **kwargs: Any) -> str | None:
        base = get_settings().wikipedia_base_url.rstrip("/")
        payload = await self.get_json(f"{base}/page/summary/{quote(title)}")
        extract = payload.get("extract")
        if isinstance(extract, str) and extract.strip():
            return extract.strip()
        return None
