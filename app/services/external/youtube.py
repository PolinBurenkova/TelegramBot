"""YouTube Data API v3 — поиск видео (требуется ключ ``YOUTUBE_API_KEY``).

Endpoint: ``https://www.googleapis.com/youtube/v3/search``. Ключ передаётся
параметром ``key``, ссылка собирается из ``id.videoId``. Контракт
медиа-провайдера:
``{"items": [{"title", "url", "source_name", "published_at"}], "source": name}``;
пустой результат → ``None``.
"""
from __future__ import annotations

from html import unescape
from typing import Any

from app.services.external.base import BaseProvider, provider_key


class YouTubeProvider(BaseProvider):
    """Поиск видео YouTube: до 50 результатов на запрос."""

    name = "youtube"
    category = "media"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ ``YOUTUBE_API_KEY``."""
        return provider_key("youtube")

    async def fetch(
        self, query: str, limit: int = 5, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Найти до ``limit`` видео; пустая выдача → ``None``."""
        if not self.api_key:
            return None
        payload = await self.get_json(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max(1, min(int(limit or 5), 50)),
                "key": self.api_key,
            },
        )
        items: list[dict[str, Any]] = []
        for entry in payload.get("items") or []:
            snippet = entry.get("snippet")
            snippet = snippet if isinstance(snippet, dict) else {}
            title = snippet.get("title")
            if not title:
                continue
            video_id = (entry.get("id") or {}).get("videoId")
            if not video_id:
                continue
            items.append(
                {
                    # YouTube отдаёт HTML-сущности в заголовках (&amp; и т.п.).
                    "title": unescape(title),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "source_name": snippet.get("channelTitle"),
                    "published_at": snippet.get("publishedAt"),
                }
            )
        if not items:
            return None
        return {"items": items, "source": self.name}
