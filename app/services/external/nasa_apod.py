"""NASA APOD — астрономическая картинка дня (ключ не обязателен).

Назначение: отдать картинку дня NASA в виде элемента ``{"title", "url",
"date", "description"}``. Ключ ``NASA_API_KEY`` подставляется, если задан,
иначе используется публичный ``DEMO_KEY``.
Ключ не требуется: https://api.nasa.gov/planetary/apod
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://api.nasa.gov/planetary/apod"
_FALLBACK_KEY = "DEMO_KEY"


def _as_text(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class NasaApodProvider(BaseProvider):
    """NASA APOD: /planetary/apod, ключ NASA_API_KEY или DEMO_KEY."""

    name = "nasa_apod"
    category = "nature"
    requires_key = False

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения (может отсутствовать)."""
        return provider_key("nasa")

    async def fetch(
        self,
        lat: float | None = None,
        lon: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Картинка дня; None, если ответ пуст или это не медиа."""
        try:
            payload = await self.get_json(
                _URL,
                params={
                    "api_key": self.api_key or _FALLBACK_KEY,
                    "thumbs": "true",
                },
            )
        except (ExternalAPIError, RateLimitError):
            return None
        if isinstance(payload, list):
            payload = payload[-1] if payload else None
        if not isinstance(payload, dict):
            return None
        title = _as_text(payload.get("title"))
        if not title:
            return None
        url = _as_text(payload.get("hdurl")) or _as_text(payload.get("url"))
        item = {
            "title": title,
            "url": url,
            "date": _as_text(payload.get("date")),
            "description": _as_text(payload.get("explanation")),
        }
        return {"items": [item], "source": self.name}
