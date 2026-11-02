"""KartaView (OpenStreetCam) — панорамы без ключа."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.kartaview import KartaViewItem
from app.services.external.base import BaseProvider


class KartaViewProvider(BaseProvider):
    """KartaView API 2.0: /photo/ рядом с координатой."""

    name = "kartaview"
    category = "panorama"
    requires_key = False

    async def fetch(
        self, lat: float, lon: float, radius: float = 0.02, **kwargs: Any
    ) -> dict[str, Any] | None:
        base = get_settings().kartaview_base_url.rstrip("/")
        payload = await self.get_json(
            f"{base}/photo/",
            params={"clat": lat, "clng": lon, "radius": radius, "page": 1, "ipp": 1},
        )
        items = (
            payload.get("currentPageItems")
            or (payload.get("result") or {}).get("data")
            or []
        )
        if not items:
            return None
        item = KartaViewItem.model_validate(items[0])
        url = item.thumb_url or item.url
        if not url:
            return None
        return {
            "image_url": url,
            "lat": lat,
            "lon": lon,
            "source": "kartaview",
        }
