"""Wikidata — короткое описание сущности. Ключ не нужен.

Action API wbsearchentities отдаёт description найденной сущности; если
описания нет, оно подтягивается через sitelinks (wbgetentities, sites=ruwiki).
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider

#: В Settings для wikidata лежит Special:EntityData, поэтому endpoint — константа.
_API_URL = "https://www.wikidata.org/w/api.php"

_SEARCH_PARAMS: dict[str, Any] = {
    "action": "wbsearchentities",
    "language": "ru",
    "uselang": "ru",
    "format": "json",
    "limit": 1,
}


class WikidataProvider(BaseProvider):
    """wikidata.org/w/api.php: description сущности по названию."""

    name = "wikidata"
    category = "wiki"
    requires_key = False

    async def fetch(self, title: str, **kwargs: Any) -> str | None:
        """Короткое описание для title или None."""
        if not title or not title.strip():
            return None
        query = title.strip()
        params = dict(_SEARCH_PARAMS, search=query)
        description = _from_search(await self.get_json(_API_URL, params=params))
        if description:
            return description
        payload = await self.get_json(
            _API_URL,
            params={
                "action": "wbgetentities",
                "sites": "ruwiki",
                "titles": query,
                "props": "descriptions",
                "languages": "ru",
                "format": "json",
            },
        )
        return _from_entities(payload)


def _from_search(payload: Any) -> str | None:
    """description первого результата wbsearchentities."""
    if not isinstance(payload, dict):
        return None
    results = payload.get("search")
    if not isinstance(results, list) or not results:
        return None
    first = results[0]
    if not isinstance(first, dict):
        return None
    for field in ("description", "label"):
        value = first.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _from_entities(payload: Any) -> str | None:
    """descriptions.ru.value из ответа wbgetentities."""
    if not isinstance(payload, dict):
        return None
    entities = payload.get("entities")
    if not isinstance(entities, dict):
        return None
    for entity in entities.values():
        if not isinstance(entity, dict):
            continue
        descriptions = entity.get("descriptions")
        if not isinstance(descriptions, dict):
            continue
        ru = descriptions.get("ru")
        if isinstance(ru, dict):
            value = ru.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None
