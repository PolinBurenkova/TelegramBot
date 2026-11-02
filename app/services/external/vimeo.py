"""Vimeo API — поиск видео (требуется токен ``VIMEO_API_KEY``/``VIMEO_ACCESS_TOKEN``).

Endpoint: ``https://api.vimeo.com/videos``.

Авторизация: Vimeo принимает заголовок ``Authorization: bearer <token>``, но
``BaseProvider.get_json`` заголовки не поддерживает, поэтому токен передаётся
параметром запроса ``access_token`` (Vimeo допускает этот способ для простых
случаев). Если API перестанет принимать query-параметр, провайдер нужно
перевести на ``httpx.AsyncClient`` с заголовком Authorization — рядом с
``YelpProvider`` в этом же пакете есть готовый пример.

Контракт медиа-провайдера:
``{"items": [{"title", "url", "source_name", "published_at"}], "source": name}``;
пустой результат → ``None``.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class VimeoProvider(BaseProvider):
    """Поиск видео Vimeo: до 100 результатов на запрос."""

    name = "vimeo"
    category = "media"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Токен ``VIMEO_API_KEY``; резервно — ``VIMEO_ACCESS_TOKEN`` из Settings."""
        token = provider_key("vimeo")
        if token:
            return token
        settings_token = get_settings().vimeo_access_token
        return settings_token.get_secret_value() if settings_token else None

    async def fetch(
        self, query: str, limit: int = 5, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Найти до ``limit`` видео; пустая выдача → ``None``."""
        if not self.api_key:
            return None
        payload = await self.get_json(
            "https://api.vimeo.com/videos",
            params={
                "query": query,
                "per_page": max(1, min(int(limit or 5), 100)),
                "fields": "uri,name,link,created_time,user.name",
                "access_token": self.api_key,
            },
        )
        items: list[dict[str, Any]] = []
        for entry in payload.get("data") or []:
            title = entry.get("name")
            if not title:
                continue
            uri = entry.get("uri")
            url = entry.get("link") or (f"https://vimeo.com{uri}" if uri else None)
            user = entry.get("user")
            items.append(
                {
                    "title": title,
                    "url": url,
                    "source_name": user.get("name") if isinstance(user, dict) else None,
                    "published_at": entry.get("created_time"),
                }
            )
        if not items:
            return None
        return {"items": items, "source": self.name}
