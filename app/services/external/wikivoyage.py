"""Wikivoyage (русский) — вводный раздел путеводителя. Ключ не нужен.

Action API: prop=extracts&exintro отдаёт только преамбулу статьи.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider

#: settings.wikivoyage_base_url указывает на REST v1, нам нужен /w/api.php.
_API_URL = "https://ru.wikivoyage.org/w/api.php"


class WikivoyageProvider(BaseProvider):
    """action=query&prop=extracts&exintro&explaintext."""

    name = "wikivoyage"
    category = "wiki"
    requires_key = False

    async def fetch(self, title: str, **kwargs: Any) -> str | None:
        """Extract (преамбула) для title или None."""
        if not title or not title.strip():
            return None
        payload = await self.get_json(
            _API_URL,
            params={
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "redirects": 1,
                "titles": title.strip(),
            },
        )
        return _first_extract(payload)


def _first_extract(payload: Any) -> str | None:
    """extract первой существующей страницы ответа action=query."""
    if not isinstance(payload, dict):
        return None
    query = payload.get("query")
    if not isinstance(query, dict):
        return None
    pages = query.get("pages")
    if not isinstance(pages, dict):
        return None
    for page in pages.values():
        if not isinstance(page, dict) or "missing" in page:
            continue
        extract = page.get("extract")
        if isinstance(extract, str) and extract.strip():
            return extract.strip()
    return None
