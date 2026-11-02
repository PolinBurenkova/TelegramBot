"""GNews — новости по запросу (требуется ключ ``GNEWS_API_KEY``).

Endpoint: ``https://gnews.io/api/v4/search``. Ключ передаётся параметром
``apikey``. Контракт медиа-провайдера:
``{"items": [{"title", "url", "source_name", "published_at"}], "source": name}``;
пустой результат → ``None``.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider, provider_key


class GNewsProvider(BaseProvider):
    """Поиск новостей GNews: не более 100 записей на запрос."""

    name = "gnews"
    category = "media"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ ``GNEWS_API_KEY`` (принимается и ``GNEWS_KEY`` из .env)."""
        return provider_key("gnews")

    async def fetch(
        self, query: str, limit: int = 5, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Найти до ``limit`` новостей; пустая выдача → ``None``."""
        if not self.api_key:
            return None
        payload = await self.get_json(
            "https://gnews.io/api/v4/search",
            params={
                "q": query,
                "lang": kwargs.get("lang", "ru"),
                "max": max(1, min(int(limit or 5), 100)),
                "apikey": self.api_key,
            },
        )
        items: list[dict[str, Any]] = []
        for article in payload.get("articles") or []:
            title = article.get("title")
            if not title:
                continue
            source = article.get("source")
            items.append(
                {
                    "title": title,
                    "url": article.get("url"),
                    "source_name": source.get("name") if isinstance(source, dict) else None,
                    "published_at": article.get("publishedAt"),
                }
            )
        if not items:
            return None
        return {"items": items, "source": self.name}
