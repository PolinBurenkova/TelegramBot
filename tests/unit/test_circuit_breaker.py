# tests/unit/test_circuit_breaker.py
"""Юнит-тесты CircuitBreaker (`app/utils/circuit_breaker.py`).

Breaker работает поверх in-memory Redis-заглушки из `app.utils.cache`,
поэтому ни сеть, ни реальный Redis не нужны. Время не подменяется:
для перевода в HALF_OPEN используется recovery_timeout=0.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.exceptions import ExternalAPIError
from app.utils.cache import InMemoryRedis
from app.utils.circuit_breaker import CircuitBreaker, CircuitState

PROVIDER = "geonames"


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _HttpError(Exception):
    """Исключение с HTTP-ответом — так breaker отличает 4xx от сбоев."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"http {status_code}")
        self.response = _FakeResponse(status_code)


def make_breaker(
    redis: InMemoryRedis,
    *,
    failure_threshold: int = 2,
    recovery_timeout: int = 60,
) -> CircuitBreaker:
    return CircuitBreaker(
        redis,
        PROVIDER,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )


async def test_initial_state_is_closed() -> None:
    breaker = make_breaker(InMemoryRedis())

    assert await breaker.get_state() is CircuitState.CLOSED
    assert await breaker.is_open() is False


async def test_successful_call_returns_result_and_stays_closed() -> None:
    breaker = make_breaker(InMemoryRedis())

    async def ok(*args: Any, **kwargs: Any) -> str:
        return f"ok:{args[0]}:{kwargs.get('n')}"

    result = await breaker.call(ok, 1, n=2)

    assert result == "ok:1:2"
    assert await breaker.get_state() is CircuitState.CLOSED


async def test_failures_below_threshold_keep_circuit_closed() -> None:
    redis = InMemoryRedis()
    breaker = make_breaker(redis, failure_threshold=3)

    async def boom() -> None:
        raise ExternalAPIError("provider down")

    for _ in range(2):
        with pytest.raises(ExternalAPIError):
            await breaker.call(boom)

    assert await breaker.get_state() is CircuitState.CLOSED
    assert await redis.get(f"cb:{PROVIDER}:failures") == "2"


async def test_threshold_failures_open_circuit_and_block_calls() -> None:
    breaker = make_breaker(InMemoryRedis(), failure_threshold=2)
    calls: list[int] = []

    async def boom() -> None:
        calls.append(1)
        raise ExternalAPIError("provider down")

    for _ in range(2):
        with pytest.raises(ExternalAPIError):
            await breaker.call(boom)

    assert await breaker.get_state() is CircuitState.OPEN
    assert await breaker.is_open() is True

    with pytest.raises(ExternalAPIError) as exc_info:
        await breaker.call(boom)

    assert "OPEN" in exc_info.value.message
    assert exc_info.value.provider == PROVIDER
    assert len(calls) == 2


async def test_success_resets_failure_counter() -> None:
    redis = InMemoryRedis()
    breaker = make_breaker(redis, failure_threshold=2)

    async def boom() -> None:
        raise ExternalAPIError("provider down")

    async def ok() -> str:
        return "ok"

    with pytest.raises(ExternalAPIError):
        await breaker.call(boom)

    assert await breaker.call(ok) == "ok"
    assert await redis.get(f"cb:{PROVIDER}:failures") is None


async def test_client_4xx_error_is_not_counted_as_failure() -> None:
    redis = InMemoryRedis()
    breaker = make_breaker(redis, failure_threshold=1)

    async def not_found() -> None:
        raise _HttpError(404)

    for _ in range(3):
        with pytest.raises(_HttpError):
            await breaker.call(not_found)

    assert await breaker.get_state() is CircuitState.CLOSED
    assert await redis.get(f"cb:{PROVIDER}:failures") is None


async def test_rate_limit_429_is_counted_as_failure() -> None:
    breaker = make_breaker(InMemoryRedis(), failure_threshold=1)

    async def too_many() -> None:
        raise _HttpError(429)

    with pytest.raises(_HttpError):
        await breaker.call(too_many)

    assert await breaker.get_state() is CircuitState.OPEN


async def test_half_open_after_recovery_closes_on_success() -> None:
    redis = InMemoryRedis()
    breaker = make_breaker(redis, failure_threshold=1, recovery_timeout=0)

    async def boom() -> None:
        raise ExternalAPIError("provider down")

    async def ok() -> str:
        return "recovered"

    with pytest.raises(ExternalAPIError):
        await breaker.call(boom)

    assert await breaker.get_state() is CircuitState.HALF_OPEN
    assert await breaker.call(ok) == "recovered"
    assert await breaker.get_state() is CircuitState.CLOSED


async def test_half_open_failure_reopens_circuit() -> None:
    redis = InMemoryRedis()
    breaker = make_breaker(redis, failure_threshold=1, recovery_timeout=0)

    async def boom() -> None:
        raise ExternalAPIError("provider down")

    with pytest.raises(ExternalAPIError):
        await breaker.call(boom)

    assert await breaker.get_state() is CircuitState.HALF_OPEN

    with pytest.raises(ExternalAPIError):
        await breaker.call(boom)

    assert await redis.get(f"cb:{PROVIDER}:state") == CircuitState.OPEN.value


async def test_unknown_state_value_is_treated_as_closed() -> None:
    redis = InMemoryRedis()
    await redis.set(f"cb:{PROVIDER}:state", "broken")
    breaker = make_breaker(redis)

    assert await breaker.get_state() is CircuitState.CLOSED
    assert await breaker.is_open() is False
