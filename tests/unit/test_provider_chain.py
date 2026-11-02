# tests/utils/test_provider_chain.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from fakeredis.aioredis import FakeRedis

from app.exceptions import AllProvidersFailedError, ExternalAPIError, QuotaExhaustedError
from app.utils.provider_chain import ProviderChain


def make_provider(name: str, *, configured=True, result=None, error=None):
    p = MagicMock()
    p.name = name
    p.is_configured = configured
    p.breaker = None
    method = AsyncMock()
    if error is not None:
        method.side_effect = error
    else:
        method.return_value = result
    p.fetch = method
    # chain вызывает getattr(provider, method_name) → нужен атрибут fetch
    return p


@pytest.fixture
def quota():
    q = MagicMock()
    q.is_exhausted = AsyncMock(return_value=False)
    q.record_usage = AsyncMock()
    return q


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.mark.asyncio
async def test_first_fails_second_succeeds(quota, redis):
    p1 = make_provider("p1", error=ExternalAPIError("boom", provider="p1"))
    p2 = make_provider("p2", result={"city": "Moscow"})
    chain = ProviderChain("cities", [p1, p2], quota, redis)

    result = await chain.call("fetch", query="Moscow")

    assert result.provider_used == "p2"
    assert result.value == {"city": "Moscow"}
    quota.record_usage.assert_awaited_once_with("p2")


@pytest.mark.asyncio
async def test_all_fail_raises(quota, redis):
    p1 = make_provider("p1", error=ExternalAPIError("boom", provider="p1"))
    p2 = make_provider("p2", error=ExternalAPIError("boom2", provider="p2"))
    chain = ProviderChain("cities", [p1, p2], quota, redis)

    with pytest.raises(AllProvidersFailedError) as ei:
        await chain.call("fetch")
    assert ei.value.chain_name == "cities"
    assert len(ei.value.attempts) == 2


@pytest.mark.asyncio
async def test_skips_unconfigured_and_quota_exhausted(quota, redis):
    unconfigured = make_provider("unconfigured", configured=False)
    exhausted = make_provider("exhausted", result="must not run")
    available = make_provider("available", result="ok")
    quota.is_exhausted = AsyncMock(side_effect=[True, False])
    chain = ProviderChain("cities", [unconfigured, exhausted, available], quota, redis)

    result = await chain.call("fetch")

    assert result.provider_used == "available"
    unconfigured.fetch.assert_not_awaited()
    exhausted.fetch.assert_not_awaited()
    available.fetch.assert_awaited_once()
    assert [attempt.reason for attempt in result.attempts[:2]] == [
        "not_configured", "quota_exhausted",
    ]


@pytest.mark.asyncio
async def test_quota_429_marks_and_continues(quota, redis):
    p1 = make_provider("p1", error=QuotaExhaustedError("q", provider="p1"))
    p2 = make_provider("p2", result="ok")
    chain = ProviderChain("cities", [p1, p2], quota, redis)

    result = await chain.call("fetch")
    assert result.provider_used == "p2"
    assert quota.record_usage.await_count >= 1