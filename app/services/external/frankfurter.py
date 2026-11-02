"""Frankfurter — курсы валют ЕЦБ, ключ не нужен.

Назначение: отдать курс ``base -> target`` из ``/latest?from=&to=``.
Ключ не требуется, API бесплатный и без регистрации.
API: https://api.frankfurter.app/latest?from={base}&to={target}
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_URL = "https://api.frankfurter.app/latest"


def _as_rate(value: Any) -> float | None:
    """Курс как положительный float, иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    return rate if rate > 0 else None


class FrankfurterProvider(BaseProvider):
    """Frankfurter (данные ЕЦБ): /latest?from=&to=, без ключа."""

    name = "frankfurter"
    category = "exchange"
    requires_key = False

    async def fetch(
        self,
        base: str = "RUB",
        target: str = "USD",
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Курс ``base -> target``; None, если валютной пары нет."""
        base_code = (base or "RUB").strip().upper()
        target_code = (target or "USD").strip().upper()
        try:
            payload = await self.get_json(
                _URL,
                params={"from": base_code, "to": target_code},
            )
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
