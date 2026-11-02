"""Mapillary — уличные панорамы (требует токен)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.mapillary import MapillaryImage
from app.services.external.base import BaseProvider


class MapillaryProvider(BaseProvider):
    """Graph API v4: /images?bbox=…&fields=thumb_1024_url."""

    name = "mapillary"
    category = "panorama"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        key = get_settings().mapillary_token
        return key.get_secret_value() if key else None

    async def fetch(
        self, lat: float, lon: float, radius: float = 0.02, **kwargs: Any
    ) -> dict[str, Any] | None:
        key = self.api_key
        if not key:
            return None
        bbox = (
            f"{lon - radius},{lat - radius * 0.5},"
            f"{lon + radius},{lat + radius * 0.5}"
        )
        payload = await self.get_json(
            "https://graph.mapillary.com/images",
            params={
                "access_token": key,
                "bbox": bbox,
                "fields": "thumb_1024_url,geometry",
                "limit": 1,
            },
        )
        items = payload if isinstance(payload, list) else payload.get("data", [])
        if not items:
            return None
        image = MapillaryImage.model_validate(items[0])
        if not image.thumb_1024_url:
            return None
        return {
            "image_url": image.thumb_1024_url,
            "lat": lat,
            "lon": lon,
            "source": "mapillary",
        }
