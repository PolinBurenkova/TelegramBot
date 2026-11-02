"""exchangerate.host — курсы валют (ключ не нужен, access_key опционален).

Назначение: отдать курс ``base -> target`` через ``/latest``, при заданном
``EXCHANGE_API_KEY`` ключ подставляется как ``access_key``.
Ключ не требуется. API: https://api.exchangerate.host/latest
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://api.exchangerate.host/latest"


def _as_rate(value: Any) -> float | None:
    """Курс как положительный float, иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    return rate if rate > 0 else None


class ExchangeHostProvider(BaseProvider):
    """exchangerate.host: /latest, без обязательного ключа."""

    name = "exchange"
    category = "exchange"
    requires_key = False

    @property
    def api_key(self) -> str | None:
        """Опциональный ключ ``EXCHANGE_API_KEY``."""
        return provider_key("exchange")

    async def fetch(
        self,
        base: str = "RUB",
        target: str = "USD",
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Курс ``base -> target``; None, если ответ без курса."""
        base_code = (base or "RUB").strip().upper()
        target_code = (target or "USD").strip().upper()
        params: dict[str, Any] = {"base": base_code, "symbols": target_code}
        if self.api_key:
            params["access_key"] = self.api_key
        try:
            payload = await self.get_json(_URL, params=params)
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
        updated = payload.get("date")
        updated_text = str(updated).strip() if updated is not None else ""
        return {
            "base": str(payload.get("base") or base_code).strip().upper(),
            "target": target_code,
            "rate": rate,
            "updated": updated_text or None,
            "source": self.name,
        }
