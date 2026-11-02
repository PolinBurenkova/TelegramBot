"""DBpedia — abstract сущности через SPARQL. Ключ не нужен.

Эндпоинт берётся из settings.dbpedia_base_url (ru.dbpedia.org/sparql);
ответ ожидается в формате SPARQL JSON (results.bindings).
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class DBpediaProvider(BaseProvider):
    """SPARQL: dbo:abstract для русской rdfs:label."""

    name = "dbpedia"
    category = "wiki"
    requires_key = False

    async def fetch(self, title: str, **kwargs: Any) -> str | None:
        """Русский abstract для title или None."""
        if not title or not title.strip():
            return None
        base = get_settings().dbpedia_base_url.rstrip("/")
        payload = await self.get_json(
            base,
            params={
                "query": _abstract_query(title.strip()),
                "format": "application/sparql-results+json",
            },
        )
        return _abstract_from_bindings(payload)


def _abstract_query(title: str) -> str:
    """SPARQL-запрос: abstract на русском по точной метке."""
    escaped = title.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "SELECT ?abstract WHERE { "
        f'?place rdfs:label "{escaped}"@ru . '
        "?place dbo:abstract ?abstract . "
        'FILTER(LANG(?abstract) = "ru") '
        "} LIMIT 1"
    )


def _abstract_from_bindings(payload: Any) -> str | None:
    """Значение ?abstract из SPARQL JSON."""
    if not isinstance(payload, dict):
        return None
    results = payload.get("results")
    if not isinstance(results, dict):
        return None
    bindings = results.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        return None
    first = bindings[0]
    if not isinstance(first, dict):
        return None
    return _binding_value(first.get("abstract"))


def _binding_value(node: Any) -> str | None:
    """Строковое значение узла SPARQL-привязки."""
    if not isinstance(node, dict):
        return None
    value = node.get("value")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
