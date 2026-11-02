"""Nager.Date — государственные праздники (ключ не нужен).

Назначение: отдать список праздников страны за год. Ответ API — массив
объектов (не dict), поэтому разбор идёт по списку с защитой от мусора.
Ключ не требуется.
API: https://date.nager.at/api/v3/PublicHolidays/{year}/{country}
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_BASE_URL = "https://date.nager.at/api/v3/PublicHolidays"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _as_text(value: Any) -> str | None:
    """Привести значение к непустой строке, иначе None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class NagerDateProvider(BaseProvider):
    """Nager.Date: /PublicHolidays/{year}/{country}, без ключа."""

    name = "nager_date"
    category = "holidays"
    requires_key = False

    async def fetch(
        self,
        country_code: str = "RU",
        year: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Праздники страны за год; None, если список пуст."""
        code = (country_code or "RU").strip().upper()
        year_value = year if isinstance(year, int) else None
        if year_value is None:
            year_value = datetime.now(timezone.utc).year
        try:
            payload = await self.get_json(f"{_BASE_URL}/{year_value}/{code}")
        except (ExternalAPIError, RateLimitError):
            return None
        if isinstance(payload, dict):
            raw_items: list[Any] = []
            for key in ("holidays", "items", "data"):
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    raw_items = candidate
                    break
        elif isinstance(payload, list):
            raw_items = payload
        else:
            return None
        holidays: list[dict[str, str]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            date = _as_text(item.get("date"))
            if not date or not _DATE_RE.match(date):
                continue
            name = _as_text(item.get("localName")) or _as_text(item.get("name"))
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
