"""NewsAPI.org — новости по запросу (требуется ключ ``NEWSAPI_API_KEY``).

Endpoint: ``https://newsapi.org/v2/everything``. Ключ передаётся параметром
``apiKey`` (сервис также принимает заголовок ``X-Api-Key``, но ``get_json``
заголовки не поддерживает). Контракт медиа-провайдера:
``{"items": [{"title", "url", "source_name", "published_at"}], "source": name}``;
пустой результат → ``None``.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider, provider_key


class NewsAPIProvider(BaseProvider):
    """Поиск новостей NewsAPI: не более 100 записей на запрос."""

    name = "newsapi"
    category = "media"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ ``NEWSAPI_API_KEY`` (принимается и ``NEWSAPI_KEY``)."""
        return provider_key("newsapi")

    async def fetch(
        self, query: str, limit: int = 5, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Найти до ``limit`` новостей; пустая выдача → ``None``."""
        if not self.api_key:
            return None
        payload = await self.get_json(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": kwargs.get("language", "ru"),
                "pageSize": max(1, min(int(limit or 5), 100)),
                "sortBy": "publishedAt",
                "apiKey": self.api_key,
            },
        )
        if payload.get("status") == "error":
            return None
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
