"""World Bank — статистика по стране, ключ не нужен.

Endpoint: ``https://api.worldbank.org/v2/country/{code}/indicator/{indicator}``
с ``format=json``. Категория ``nature``: справочные показатели (население и
другие индикаторы) для раздела «природа и статистика». Контракт:
``{"country_code", "indicator", "value", "year", "source"}``.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider, provider_key

# Индикатор по умолчанию — население, всего населения.
DEFAULT_INDICATOR = "SP.POP.TOTL"


def _to_float(value: Any) -> float | None:
    """Привести значение к float; None/мусор → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class WorldBankProvider(BaseProvider):
    """World Bank Indicators API: ключ не нужен, лимитов по ключу нет."""

    name = "world_bank"
    category = "nature"
    requires_key = False

    @property
    def api_key(self) -> str | None:
        """Ключ не требуется; свойство оставлено для единого контракта."""
        return provider_key("world_bank")

    async def fetch(
        self, country_code: str, indicator: str = DEFAULT_INDICATOR, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Значение индикатора (по умолчанию население) и год наблюдения."""
        code = country_code.strip().upper()
        if not code:
            return None
        payload = await self.get_json(
            f"https://api.worldbank.org/v2/country/{code}/indicator/{indicator}",
            params={"format": "json", "per_page": 5},
        )
        if not isinstance(payload, list) or len(payload) < 2:
            return None
        rows = payload[1]
        if not isinstance(rows, list) or not rows:
            return None
        row: Any = next(
            (item for item in rows if isinstance(item, dict) and item.get("value") is not None),
            rows[0],
        )
        if not isinstance(row, dict):
            return None
        year = row.get("date")
        return {
            "country_code": code,
            "indicator": indicator,
            "value": _to_float(row.get("value")),
            "year": str(year) if year is not None else None,
            "source": self.name,
        }
