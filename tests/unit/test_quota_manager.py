# tests/utils/test_quota_manager.py
import pytest
from fakeredis.aioredis import FakeRedis

from app.exceptions import QuotaExhaustedError
from app.utils.quota_manager import QuotaManager


@pytest.mark.asyncio
async def test_exhausted_after_limit():
    redis = FakeRedis()
    limits = {"test_provider": {"period": "day", "limit": 3}}
    q = QuotaManager(redis, limits)

    for _ in range(3):
        assert await q.can_use("test_provider")
        await q.record_usage("test_provider")

    assert not await q.can_use("test_provider")
    assert await q.is_exhausted("test_provider")

    usage = await q.get_usage("test_provider")
    assert usage["used"] == 3
    assert usage["limit"] == 3
    assert usage["exhausted"] is True


@pytest.mark.asyncio
async def test_unlimited_always_true():
    redis = FakeRedis()
    q = QuotaManager(redis, {"open_meteo": {"period": "unlimited", "limit": 0}})
    for _ in range(100):
        assert await q.can_use("open_meteo")
    await q.record_usage("open_meteo")  # no-op


@pytest.mark.asyncio
async def test_reset_clears_state():
    redis = FakeRedis()
    limits = {"p": {"period": "day", "limit": 2}}
    q = QuotaManager(redis, limits)
    for _ in range(2):
        await q.record_usage("p")
    assert await q.is_exhausted("p")
    await q.reset("p")
    assert not await q.is_exhausted("p")
    assert (await q.get_usage("p"))["used"] == 0