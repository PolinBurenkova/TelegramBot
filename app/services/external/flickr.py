"""Flickr — фото города. Нужен ключ FLICKR_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class FlickrProvider(BaseProvider):
    """REST API Flickr (flickr.photos.search): запрос → URL изображения."""

    name = "flickr"
    category = "photo"
    requires_key = True
    base_url = "https://www.flickr.com/services/rest"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (FLICKR_API_KEY)."""
        key = get_settings().flickr_api_key
        return key.get_secret_value() if key else provider_key("flickr")

    async def fetch(self, query: str, **kwargs: Any) -> str | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "method": "flickr.photos.search",
                "api_key": self.api_key,
                "text": query,
                "per_page": 1,
                "sort": "relevance",
                "media": "photos",
                "content_type": 1,
                "safe_search": 1,
                "extras": "url_l,url_c,url_z",
                "format": "json",
                "nojsoncallback": 1,
            },
        )
        if not isinstance(payload, dict):
            return None
        photos = payload.get("photos")
        items = photos.get("photo") if isinstance(photos, dict) else None
        if not isinstance(items, list) or not items:
            return None
        photo = items[0]
        if not isinstance(photo, dict):
            return None
        for field in ("url_l", "url_c", "url_z"):
            url = photo.get(field)
            if isinstance(url, str) and url:
                return url
        farm = photo.get("farm")
        server = photo.get("server")
        photo_id = photo.get("id")
        secret = photo.get("secret")
        if not all((farm, server, photo_id, secret)):
            return None
        return f"https://farm{farm}.staticflickr.com/{server}/{photo_id}_{secret}_b.jpg"
