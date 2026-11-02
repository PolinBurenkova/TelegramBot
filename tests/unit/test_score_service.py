# tests/utils/test_circuit_breaker.py
import asyncio
import pytest
from fakeredis.aioredis import FakeRedis

from app.exceptions import ExternalAPIError
from app.utils.circuit_breaker import CircuitBreaker, CircuitState


@pytest.mark.asyncio
async def test_opens_after_threshold(monkeypatch):
    redis = FakeRedis()
    cb = CircuitBreaker(redis, "p", failure_threshold=5, recovery_timeout=60)

    async def boom():
        raise ExternalAPIError("x", provider="p")

    for _ in range(5):
        with pytest.raises(ExternalAPIError):
            await cb.call(boom)
    assert await cb.get_state() is CircuitState.OPEN

    # OPEN → вызов отклоняется без реального вызова
    called = {"n": 0}
    async def ok():
        called["n"] += 1
        return "ok"
    with pytest.raises(ExternalAPIError):
        await cb.call(ok)
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_half_open_after_timeout(monkeypatch):
    redis = FakeRedis()
    cb = CircuitBreaker(redis, "p", failure_threshold=1, recovery_timeout=1)

    async def boom():
        raise ExternalAPIError("x", provider="p")
    with pytest.raises(ExternalAPIError):
        await cb.call(boom)
    assert await cb.get_state() is CircuitState.OPEN

    await asyncio.sleep(1.05)
    assert await cb.get_state() is CircuitState.HALF_OPEN

    async def ok():
        return "ok"
    assert await cb.call(ok) == "ok"
    assert await cb.get_state() is CircuitState.CLOSED