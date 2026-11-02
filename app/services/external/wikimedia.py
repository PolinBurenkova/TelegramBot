"""Wikimedia Commons — фото города. Ключ не нужен."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.wikimedia import WikimediaResponse
from app.services.external.base import BaseProvider


class WikimediaProvider(BaseProvider):
    """MediaWiki API Commons: generator=search + imageinfo."""

    name = "wikimedia"
    category = "photo"
    requires_key = False

    async def fetch(self, query: str, **kwargs: Any) -> str | None:
        base = get_settings().wikimedia_commons_base_url.rstrip("/")
        payload = await self.get_json(
            base,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrlimit": 1,
                "gsrnamespace": 6,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 1024,
            },
        )
        data = WikimediaResponse.model_validate(payload)
        if data.query is None:
            return None
        for page in data.query.pages.values():
            for info in page.imageinfo:
                if info.thumburl or info.url:
                    return info.thumburl or info.url
        return None
