"""Pixabay — фото города. Нужен ключ PIXABAY_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class PixabayProvider(BaseProvider):
    """Image Search API Pixabay: запрос → прямой URL изображения."""

    name = "pixabay"
    category = "photo"
    requires_key = True
    base_url = "https://pixabay.com/api/"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (PIXABAY_API_KEY)."""
        key = get_settings().pixabay_api_key
        return key.get_secret_value() if key else provider_key("pixabay")

    async def fetch(self, query: str, **kwargs: Any) -> str | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "key": self.api_key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 3,
                "lang": "ru",
            },
        )
        if not isinstance(payload, dict):
            return None
        hits = payload.get("hits") or []
        if not isinstance(hits, list) or not hits:
            return None
        item = hits[0]
        if not isinstance(item, dict):
            return None
        return item.get("largeImageURL") or item.get("webformatURL") or item.get("previewURL")
