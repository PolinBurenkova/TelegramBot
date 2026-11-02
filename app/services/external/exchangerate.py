"""open.er-api.com (ExchangeRate-API) — курс валют, ключ не нужен.

Назначение: отдать курс ``base -> target`` из открытого эндпоинта
``/v6/latest/{base}``. Ключ не требуется (лимит запросов на IP).
API: https://open.er-api.com/v6/latest/{base}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_BASE_URL = "https://open.er-api.com/v6/latest"


def _as_rate(value: Any) -> float | None:
    """Курс как положительный float, иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    return rate if rate > 0 else None


def _as_updated(value: Any) -> str | None:
    """Время обновления курса из unix timestamp или строки."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            moment = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return moment.isoformat()
    text = str(value).strip()
    return text or None


class ExchangeRateProvider(BaseProvider):
    """ExchangeRate-API (open access): /v6/latest/{base}, без ключа."""

    name = "exchangerate"
    category = "exchange"
    requires_key = False

    async def fetch(
        self,
        base: str = "RUB",
        target: str = "USD",
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Курс ``base -> target``; None, если курса в ответе нет."""
        base_code = (base or "RUB").strip().upper()
        target_code = (target or "USD").strip().upper()
        try:
            payload = await self.get_json(f"{_BASE_URL}/{base_code}")
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        rates = payload.get("rates")
        if not isinstance(rates, dict):
            return None
        rate = _as_rate(rates.get(target_code))
        if rate is None and target_code == base_code:
            rate = 1.0
        if rate is None:
            return None
        return {
            "base": str(payload.get("base_code") or base_code).strip().upper(),
            "target": target_code,
            "rate": rate,
            "updated": _as_updated(
                payload.get("time_last_update_unix") or payload.get("time_last_update_utc")
            ),
            "source": self.name,
        }
