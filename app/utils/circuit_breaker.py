"""CircuitBreaker — защита от каскадных отказов провайдера.

Состояния: CLOSED → OPEN → HALF_OPEN → CLOSED.
Состояние живёт в Redis, чтобы выживать рестарты воркеров.
Все redis-операции защищены: при недоступности Redis breaker
деградирует в CLOSED и пропускает вызовы напрямую.

Ключи:
  cb:{provider}:state        — "closed" | "open" | "half_open"
  cb:{provider}:failures     — счётчик подряд идущих ошибок
  cb:{provider}:half_open_ts — timestamp попытки в HALF_OPEN
"""
from __future__ import annotations

import time
from enum import StrEnum
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger
from redis.asyncio import Redis  # noqa: F401 — реэкспорт для типизации

from app.exceptions import AllProvidersFailedError  # noqa: F401
from app.exceptions import ExternalAPIError

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Реализация паттерна circuit breaker поверх Redis."""

    def __init__(
        self,
        redis: Redis,
        provider: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1,
    ) -> None:
        self._redis = redis
        self._provider = provider
        self._threshold = failure_threshold
        self._recovery = recovery_timeout
        self._half_open_max = half_open_max_calls

    # ─── keys ─────────────────────────────────────────────────────────────
    @property
    def _state_key(self) -> str:
        return f"cb:{self._provider}:state"

    @property
    def _failures_key(self) -> str:
        return f"cb:{self._provider}:failures"

    @property
    def _half_open_key(self) -> str:
        return f"cb:{self._provider}:half_open_ts"

    @property
    def _opened_at_key(self) -> str:
        return f"cb:{self._provider}:opened_at"

    # ─── защищённые redis-операции ───────────────────────────────────────
    async def _get(self, key: str) -> str | None:
        try:
            raw = await self._redis.get(key)  # type: ignore[union-attr]
        except Exception:
            return None
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else str(raw)

    async def _ttl(self, key: str) -> int:
        try:
            return int(await self._redis.ttl(key))  # type: ignore[union-attr]
        except Exception:
            return -1

    async def _set(
        self, key: str, value: Any, ex: int | None = None, *, nx: bool = False
    ) -> bool:
        try:
            if nx:
                return bool(
                    await self._redis.set(key, value, ex=ex, nx=True)  # type: ignore[union-attr]
                )
            await self._redis.set(key, value, ex=ex)  # type: ignore[union-attr]
            return True
        except Exception:
            return False

    async def _delete(self, *keys: str) -> None:
        try:
            await self._redis.delete(*keys)  # type: ignore[union-attr]
        except Exception:
            pass

    async def _incr(self, key: str) -> int:
        try:
            return int(await self._redis.incr(key))  # type: ignore[union-attr]
        except Exception:
            return 0

    async def _expire(self, key: str, seconds: int) -> None:
        try:
            await self._redis.expire(key, seconds)  # type: ignore[union-attr]
        except Exception:
            pass

    # ─── introspection ────────────────────────────────────────────────────
    async def get_state(self) -> CircuitState:
        raw = await self._get(self._state_key)
        if raw is None:
            return CircuitState.CLOSED
        try:
            state = CircuitState(raw)
        except ValueError:
            return CircuitState.CLOSED

        # Состояние не истекает по TTL: иначе OPEN незаметно стал бы CLOSED.
        if state is CircuitState.OPEN:
            opened_at = await self._get(self._opened_at_key)
            if opened_at is not None and time.time() - float(opened_at) >= self._recovery:
                await self._to_half_open()
                return CircuitState.HALF_OPEN
        return state

    async def is_open(self) -> bool:
        return await self.get_state() is CircuitState.OPEN

    # ─── state transitions ────────────────────────────────────────────────
    async def _to_open(self) -> None:
        await self._set(self._opened_at_key, str(time.time()))
        await self._set(self._state_key, CircuitState.OPEN.value)
        logger.bind(provider=self._provider, breaker="open").warning(
            "Circuit OPEN | provider={} recovery_in={}s",
            self._provider, self._recovery,
        )

    async def _to_closed(self) -> None:
        await self._set(self._state_key, CircuitState.CLOSED.value)
        await self._delete(self._failures_key, self._half_open_key, self._opened_at_key)
        logger.bind(provider=self._provider, breaker="closed").info(
            "Circuit CLOSED | provider={}", self._provider
        )

    async def _to_half_open(self) -> None:
        await self._set(self._state_key, CircuitState.HALF_OPEN.value)
        await self._set(self._half_open_key, str(int(time.time())))
        logger.bind(provider=self._provider, breaker="half_open").info(
            "Circuit HALF_OPEN | provider={}", self._provider
        )

    async def _record_success(self) -> None:
        state = await self.get_state()
        if state is CircuitState.HALF_OPEN:
            await self._to_closed()
        elif state is CircuitState.CLOSED:
            await self._delete(self._failures_key)

    async def _record_failure(self) -> None:
        state = await self.get_state()
        if state is CircuitState.HALF_OPEN:
            await self._to_open()
            return
        failures = await self._incr(self._failures_key)
        await self._expire(self._failures_key, self._recovery * 10)
        if failures >= self._threshold:
            await self._to_open()

    # ─── main entrypoint ──────────────────────────────────────────────────
    async def call(
        self,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        state = await self.get_state()

        if state is CircuitState.OPEN:
            raise ExternalAPIError(
                f"Circuit OPEN for {self._provider}",
                provider=self._provider,
                user_message="Провайдер временно недоступен.",
            )

        if state is CircuitState.HALF_OPEN:
            # пропускаем не более half_open_max_calls параллельных «проб»
            probe_slot = f"cb:{self._provider}:probe"
            if not await self._set(probe_slot, "1", ex=self._recovery, nx=True):
                raise ExternalAPIError(
                    f"Circuit HALF_OPEN busy for {self._provider}",
                    provider=self._provider,
                )
            try:
                result = await fn(*args, **kwargs)
                await self._record_success()
                return result
            except Exception:
                await self._record_failure()
                raise
            finally:
                await self._delete(probe_slot)

        # CLOSED
        try:
            result = await fn(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as exc:
            # 4xx (кроме 429) — вина клиента, не провайдера: не считаем сбоем
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise
            await self._record_failure()
            raise
