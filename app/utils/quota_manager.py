"""QuotaManager — учёт квот провайдеров в Redis.

Единый источник правды о лимитах — constants.QUOTA_LIMITS.
Ключи в Redis:
  quota:{provider}:{period}:{bucket}      — счётчик (int)
  quota:{provider}:exhausted:{period}     — флаг «исчерпан до конца окна»
  quota:{provider}:sec:{ts}               — окно 1 сек (для period=second)
  quota:{provider}:reset_at:{period}      — unix-ts окончания окна (для админки)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from redis.asyncio import Redis

from app.constants import QUOTA_LIMITS
from app.exceptions import QuotaExhaustedError


class QuotaManager:
    """Учёт квот по периодам: second / minute / hour / day / month / unlimited."""

    _PERIOD_SECONDS: dict[str, int] = {
        "minute": 60,
        "hour": 3_600,
        "day": 86_400,
        "month": 30 * 86_400,  # упрощённо; для точного месяца — TTL до 1-го числа
    }

    def __init__(
        self,
        redis: Redis,
        limits: dict[str, dict[str, int | str]] | None = None,
        warning_threshold: float = 0.9,
    ) -> None:
        self._redis = redis
        self._limits = limits or QUOTA_LIMITS
        self._warning_threshold = warning_threshold

    # ─── helpers ──────────────────────────────────────────────────────────
    def _cfg(self, provider: str) -> dict[str, int | str]:
        return self._limits.get(provider, {"period": "unlimited", "limit": 0})

    def _period(self, provider: str) -> str:
        return str(self._cfg(provider)["period"])

    def _limit(self, provider: str) -> int:
        return int(self._cfg(provider)["limit"])

    @staticmethod
    def _now() -> int:
        return int(time.time())

    def _bucket_key(self, provider: str, period: str) -> str:
        now = self._now()
        if period == "second":
            return f"quota:{provider}:sec:{now}"
        if period == "minute":
            bucket = now // 60
        elif period == "hour":
            bucket = now // 3_600
        elif period == "day":
            bucket = now // 86_400
        elif period == "month":
            bucket = now // (30 * 86_400)
        else:
            bucket = now
        return f"quota:{provider}:{period}:{bucket}"

    def _exhausted_key(self, provider: str, period: str) -> str:
        return f"quota:{provider}:exhausted:{period}"

    def _reset_key(self, provider: str, period: str) -> str:
        return f"quota:{provider}:reset_at:{period}"

    def _ttl_for(self, period: str) -> int:
        """TTL до конца окна (минимум 1с)."""
        now = self._now()
        if period == "second":
            return 1
        if period == "minute":
            return 60 - (now % 60) or 60
        if period == "hour":
            return 3_600 - (now % 3_600) or 3_600
        if period == "day":
            return 86_400 - (now % 86_400) or 86_400
        if period == "month":
            return self._PERIOD_SECONDS["month"] - (now % self._PERIOD_SECONDS["month"]) or 86_400
        return 86_400

    # ─── public API ───────────────────────────────────────────────────────
    async def is_exhausted(self, provider: str) -> bool:
        period = self._period(provider)
        if period == "unlimited":
            return False
        return bool(await self._redis.exists(self._exhausted_key(provider, period)))

    async def can_use(self, provider: str) -> bool:
        """True, если провайдер можно вызывать прямо сейчас."""
        period = self._period(provider)
        limit = self._limit(provider)
        if period == "unlimited" or limit <= 0:
            return True
        if await self.is_exhausted(provider):
            return False

        if period == "second":
            key = self._bucket_key(provider, "second")
            used = int(await self._redis.get(key) or 0)
            return used < limit

        key = self._bucket_key(provider, period)
        used = int(await self._redis.get(key) or 0)
        return used < limit

    async def record_usage(self, provider: str) -> None:
        """Инкремент счётчика + предупреждение на 90% + exhausted на 100%."""
        period = self._period(provider)
        limit = self._limit(provider)
        if period == "unlimited" or limit <= 0:
            return

        key = self._bucket_key(provider, period)
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self._ttl_for(period))
        used, _ = await pipe.execute()
        used = int(used)

        if used >= limit:
            ttl = self._ttl_for(period)
            reset_at = self._now() + ttl
            await self._redis.set(
                self._exhausted_key(provider, period), "1", ex=ttl
            )
            await self._redis.set(
                self._reset_key(provider, period), str(reset_at), ex=ttl
            )
            logger.bind(provider=provider, period=period).warning(
                "Quota exhausted | provider={} used={}/{} reset_at={}",
                provider, used, limit,
                datetime.fromtimestamp(reset_at, tz=timezone.utc).isoformat(),
            )
            # Успешный запрос уже использовал последний доступный слот.
            # Запрещаем следующий вызов, но не теряем текущий результат.
            return

        ratio = used / limit
        if ratio >= self._warning_threshold:
            logger.bind(provider=provider, period=period).warning(
                "Quota at {:.0%} | provider={} used={}/{}",
                ratio, provider, used, limit,
            )

    async def get_usage(self, provider: str) -> dict[str, Any]:
        period = self._period(provider)
        limit = self._limit(provider)
        if period == "unlimited":
            return {
                "used": 0, "limit": 0, "period": period,
                "reset_at": None, "exhausted": False,
            }
        used = int(await self._redis.get(self._bucket_key(provider, period)) or 0)
        reset_raw = await self._redis.get(self._reset_key(provider, period))
        reset_at = (
            datetime.fromtimestamp(int(reset_raw), tz=timezone.utc).isoformat()
            if reset_raw else None
        )
        return {
            "used": used,
            "limit": limit,
            "period": period,
            "reset_at": reset_at,
            "exhausted": await self.is_exhausted(provider),
        }

    async def reset(self, provider: str) -> None:
        """Сброс счётчиков и флагов (админ-команда)."""
        period = self._period(provider)
        keys = [
            self._bucket_key(provider, period),
            self._exhausted_key(provider, period),
            self._reset_key(provider, period),
        ]
        if period == "second":
            keys.append(self._bucket_key(provider, "second"))
        await self._redis.delete(*keys)
        logger.bind(provider=provider).info("Quota reset for provider={}", provider)