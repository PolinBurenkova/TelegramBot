"""HolidayAPI — государственные праздники (нужен ключ).

Назначение: отдать список праздников страны за год из ``/v1/holidays``.
Ответ приходит как ``{"holidays": [...]}`` либо как карта ``date -> [имена]``,
поддерживаются оба варианта.
Ключ обязателен: ``HOLIDAY_API_KEY``.
API: https://holidayapi.com/v1/holidays
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://holidayapi.com/v1/holidays"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _as_text(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> list[Any]:
    """Список праздников из списка или карты ``date -> имя``."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        items: list[Any] = []
        for date, names in value.items():
            if isinstance(names, str):
                items.append({"date": date, "name": names})
            elif isinstance(names, list):
                items.extend({"date": date, "name": name} for name in names)
        return items
    return []


class HolidayAPIProvider(BaseProvider):
    """HolidayAPI: /v1/holidays, ключ HOLIDAY_API_KEY."""

    name = "holiday_api"
    category = "holidays"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения."""
        return provider_key("holiday")

    async def fetch(
        self,
        country_code: str = "RU",
        year: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Праздники страны за год; None без ключа или без данных."""
        if not self.api_key:
            return None
        code = (country_code or "RU").strip().upper()
        year_value = year if isinstance(year, int) else None
        if year_value is None:
            year_value = datetime.now(timezone.utc).year
        try:
            payload = await self.get_json(
                _URL,
                params={
                    "key": self.api_key,
                    "country": code,
                    "year": year_value,
                    "public": "true",
                },
            )
        except (ExternalAPIError, RateLimitError):
            return None
        if isinstance(payload, list):
            raw_items: list[Any] = payload
        elif isinstance(payload, dict):
            raw_items = []
            for key in ("holidays", "items", "data"):
                candidate = payload.get(key)
                if candidate is not None:
                    raw_items = _normalize(candidate)
                    break
        else:
            return None
        holidays: list[dict[str, str]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            date = _as_text(item.get("date"))
            if not date or not _DATE_RE.match(date):
                continue
            name = _as_text(item.get("name")) or _as_text(item.get("local_name"))
            if not name:
                continue
            holidays.append({"date": date, "name": name})
        if not holidays:
            return None
        return {
            "country_code": code,
            "year": year_value,
            "holidays": holidays,
            "source": self.name,
        }
