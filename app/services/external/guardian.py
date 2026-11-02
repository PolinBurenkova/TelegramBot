"""The Guardian — новости по запросу (требуется ключ ``GUARDIAN_API_KEY``).

Endpoint: ``https://content.guardianapis.com/search``. Ключ передаётся
параметром ``api-key``, заголовок ``headline`` запрашивается через
``show-fields``. Контракт медиа-провайдера:
``{"items": [{"title", "url", "source_name", "published_at"}], "source": name}``;
пустой результат → ``None``.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider, provider_key


class GuardianProvider(BaseProvider):
    """Content API The Guardian: поиск по архиву, не более 50 записей."""

    name = "guardian"
    category = "media"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ ``GUARDIAN_API_KEY``."""
        return provider_key("guardian")

    async def fetch(
        self, query: str, limit: int = 5, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Найти до ``limit`` материалов; пустая выдача → ``None``."""
        if not self.api_key:
            return None
        payload = await self.get_json(
            "https://content.guardianapis.com/search",
            params={
                "q": query,
                "page-size": max(1, min(int(limit or 5), 50)),
                "order-by": "newest",
                "show-fields": "headline,shortUrl",
                "api-key": self.api_key,
            },
        )
        response = payload.get("response")
        if not isinstance(response, dict):
            return None
        items: list[dict[str, Any]] = []
        for entry in response.get("results") or []:
            fields = entry.get("fields")
            fields = fields if isinstance(fields, dict) else {}
            title = fields.get("headline") or entry.get("webTitle")
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "url": fields.get("shortUrl") or entry.get("webUrl"),
                    "source_name": "The Guardian",
                    "published_at": entry.get("webPublicationDate"),
                }
            )
        if not items:
            return None
        return {"items": items, "source": self.name}
