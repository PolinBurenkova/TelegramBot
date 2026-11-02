"""Open Exchange Rates — курсы валют к USD (нужен ключ).

Назначение: отдать курс ``base -> target``. Free-план привязан к базе USD,
поэтому при ``base != "USD"`` курс считается кросс-пересчётом через USD.
Ключ обязателен: ``OPEN_EXCHANGE_RATES_API_KEY``.
API: https://openexchangerates.org/api/latest.json
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://openexchangerates.org/api/latest.json"


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
    """Время обновления из unix timestamp или строки."""
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


class OpenExchangeRatesProvider(BaseProvider):
    """Open Exchange Rates: /api/latest.json, ключ OPEN_EXCHANGE_RATES_API_KEY."""

    name = "open_exchange_rates"
    category = "exchange"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения."""
        return provider_key("open_exchange_rates")

    async def fetch(
        self,
        base: str = "RUB",
        target: str = "USD",
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Курс ``base -> target`` через базу USD; None без ключа/курса."""
        if not self.api_key:
            return None
        base_code = (base or "RUB").strip().upper()
        target_code = (target or "USD").strip().upper()
        try:
            payload = await self.get_json(_URL, params={"app_id": self.api_key})
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        rates = payload.get("rates")
        if not isinstance(rates, dict):
            return None
        usd_rate = 1.0 if base_code == "USD" else _as_rate(rates.get(base_code))
        target_rate = 1.0 if target_code == "USD" else _as_rate(rates.get(target_code))
        if usd_rate is None or target_rate is None:
            return None
        rate = target_rate / usd_rate
        if rate <= 0:
            return None
        return {
            "base": base_code,
            "target": target_code,
            "rate": rate,
            "updated": _as_updated(payload.get("timestamp")),
            "source": self.name,
        }
