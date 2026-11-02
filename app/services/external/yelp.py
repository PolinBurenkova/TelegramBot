"""Yelp Fusion — поиск мест рядом (требуется ключ ``YELP_API_KEY``).

Endpoint: ``https://api.yelp.com/v3/businesses/search``. Авторизация только
через заголовок ``Authorization: Bearer <key>``, а ``BaseProvider.get_json``
заголовки не поддерживает, поэтому запрос уходит через ``httpx.AsyncClient``
внутри провайдера (как в ``libretranslate.py``); любая ошибка → ``None``.

Контракт POI:
``{"items": [{"name", "lat", "lon", "category"}], "source": name}``;
пустой результат → ``None``.
"""
from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.services.external.base import BaseProvider, provider_key

# Yelp: radius в метрах (1…40 000), limit 1…50.
MAX_RADIUS_M = 40_000
MAX_LIMIT = 50


def _to_float(value: Any) -> float | None:
    """Привести значение к float; None/мусор → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class YelpProvider(BaseProvider):
    """Yelp Fusion: поиск организаций вокруг точки."""

    name = "yelp"
    category = "poi"
    requires_key = True
    base_url = "https://api.yelp.com/v3/businesses/search"

    @property
    def api_key(self) -> str | None:
        """Ключ ``YELP_API_KEY``."""
        return provider_key("yelp")

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        radius: int = 1_000,
        limit: int = 5,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Найти до ``limit`` мест в радиусе ``radius`` метров; сбой → ``None``."""
        key = self.api_key
        if not key:
            return None
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": max(1, min(int(radius or 1_000), MAX_RADIUS_M)),
            "limit": max(1, min(int(limit or 5), MAX_LIMIT)),
        }
        categories = kwargs.get("categories")
        if categories:
            params["categories"] = categories
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning("{}: поиск не удался: {}", self.name, exc)
            return None
        if not isinstance(data, dict):
            return None
        items: list[dict[str, Any]] = []
        for business in data.get("businesses") or []:
            name = business.get("name")
            if not name:
                continue
            coordinates = business.get("coordinates")
            coordinates = coordinates if isinstance(coordinates, dict) else {}
            business_categories = business.get("categories") or []
            category: str | None = None
            if business_categories and isinstance(business_categories[0], dict):
                first = business_categories[0]
                category = first.get("title") or first.get("alias")
            items.append(
                {
                    "name": name,
                    "lat": _to_float(coordinates.get("latitude")),
                    "lon": _to_float(coordinates.get("longitude")),
                    "category": category,
                }
            )
        if not items:
            return None
        return {"items": items, "source": self.name}
