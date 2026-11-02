# tests/unit/test_cache.py
"""Юнит-тесты кэша и in-memory Redis-заглушки (`app/utils/cache.py`).

Сеть не используется: MemoryCache и InMemoryRedis работают в памяти,
а `create_cache()`/`get_redis()` возвращают их же, т.к. conftest
выставляет REDIS_URL="" (без обращения к серверу Redis).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.utils.cache import InMemoryRedis, MemoryCache, create_cache, get_cache, get_redis


@pytest.fixture()
def cache() -> MemoryCache:
    return MemoryCache()


async def test_get_missing_key_returns_none(cache: MemoryCache) -> None:
    assert await cache.get("absent") is None


async def test_set_and_get_roundtrip_preserves_unicode(cache: MemoryCache) -> None:
    value = {"city": "Москва", "score": 42, "ok": True, "lost": None}

    await cache.set("user:1", value, ttl=60)

    assert await cache.get("user:1") == value


async def test_expired_value_is_dropped(cache: MemoryCache) -> None:
    await cache.set("short", "value", ttl=-1)

    assert await cache.get("short") is None
    assert "short" not in cache._data


async def test_delete_and_delete_pattern(cache: MemoryCache) -> None:
    await cache.set("cities:1", 1, ttl=60)
    await cache.set("cities:2", 2, ttl=60)
    await cache.set("weather:1", 3, ttl=60)

    await cache.delete("cities:1")
    await cache.delete_pattern("cities:*")

    assert await cache.get("cities:1") is None
    assert await cache.get("cities:2") is None
    assert await cache.get("weather:1") == 3


async def test_get_or_set_calls_factory_once(cache: MemoryCache) -> None:
    calls: list[int] = []

    async def factory() -> dict[str, int]:
        calls.append(1)
        return {"n": len(calls)}

    first = await cache.get_or_set("key", 60, factory)
    second = await cache.get_or_set("key", 60, factory)

    assert first == {"n": 1}
    assert second == {"n": 1}
    assert len(calls) == 1


async def test_get_or_set_does_not_cache_none(cache: MemoryCache) -> None:
    calls: list[int] = []

    async def factory() -> None:
        calls.append(1)
        return None

    assert await cache.get_or_set("none", 60, factory) is None
    assert await cache.get_or_set("none", 60, factory) is None
    assert len(calls) == 2
    assert await cache.get("none") is None


async def test_close_clears_data(cache: MemoryCache) -> None:
    await cache.set("key", "value", ttl=60)

    await cache.close()

    assert await cache.get("key") is None


def test_create_cache_is_memory_without_redis_url() -> None:
    assert isinstance(create_cache(), MemoryCache)


def test_get_cache_returns_singleton() -> None:
    assert get_cache() is get_cache()


def test_get_redis_falls_back_to_memory() -> None:
    assert isinstance(get_redis(), InMemoryRedis)


async def test_in_memory_redis_set_nx() -> None:
    redis = InMemoryRedis()

    assert await redis.set("k", "1", nx=True) is True
    assert await redis.set("k", "2", nx=True) is False
    assert await redis.get("k") == "1"


async def test_in_memory_redis_ttl_states() -> None:
    redis = InMemoryRedis()

    assert await redis.ttl("missing") == -2

    await redis.set("forever", "1")
    assert await redis.ttl("forever") == -1

    await redis.set("short", "1", ex=100)
    ttl = await redis.ttl("short")
    assert 0 < ttl <= 100


async def test_in_memory_redis_incr_and_expire() -> None:
    redis = InMemoryRedis()

    assert await redis.incr("counter") == 1
    assert await redis.incr("counter") == 2
    assert await redis.get("counter") == "2"
    assert await redis.expire("counter", 30) is True
    assert await redis.expire("absent", 30) is False
    assert await redis.delete("counter") == 1
    assert await redis.exists("counter") == 0


async def test_in_memory_redis_pipeline() -> None:
    redis = InMemoryRedis()

    results: list[Any] = await redis.pipeline().incr("quota:day").expire("quota:day", 60).execute()

    assert results[0] == 1
    assert results[1] is True
    assert await redis.get("quota:day") == "1"
