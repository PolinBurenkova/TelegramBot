"""Unsplash — фото города. Нужен ключ UNSPLASH_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class UnsplashProvider(BaseProvider):
    """Search Photos API Unsplash: запрос → прямой URL изображения."""

    name = "unsplash"
    category = "photo"
    requires_key = True
    base_url = "https://api.unsplash.com/search/photos"

    @property
    def api_key(self) -> str | None:
        """Access Key из Settings, иначе из окружения (UNSPLASH_API_KEY)."""
        key = get_settings().unsplash_access_key
        return key.get_secret_value() if key else provider_key("unsplash")

    async def fetch(self, query: str, **kwargs: Any) -> str | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "query": query,
                "per_page": 1,
                "orientation": "landscape",
                "client_id": self.api_key,
            },
        )
        if not isinstance(payload, dict):
            return None
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            return None
        item = results[0]
        urls = item.get("urls") if isinstance(item, dict) else None
        if not isinstance(urls, dict):
            return None
        return urls.get("regular") or urls.get("full") or urls.get("small")
