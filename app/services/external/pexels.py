"""Pexels — фотографии городов (бесплатный ключ)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class PexelsProvider(BaseProvider):
    """Pexels API v1 /search: первое горизонтальное фото по запросу."""

    name = "pexels"
    category = "photo"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        settings = get_settings()
        configured = getattr(settings, "pexels_api_key", None)
        if configured:
            return (
                configured.get_secret_value()
                if hasattr(configured, "get_secret_value")
                else str(configured)
            )
        return provider_key("pexels")

    async def fetch(self, query: str, **kwargs: Any) -> str | None:
        """URL фото (large2x/large) или None."""
        key = self.api_key
        if not key:
            return None
        payload = await self.get_json(
            "https://api.pexels.com/v1/search",
            params={
                "query": query,
                "per_page": 1,
                "orientation": "landscape",
            },
        )
        if not isinstance(payload, dict):
            return None
        photos = payload.get("photos") or []
        if not photos:
            return None
        src = (photos[0] or {}).get("src") or {}
        if not isinstance(src, dict):
            return None
        return src.get("large2x") or src.get("large") or src.get("original")
