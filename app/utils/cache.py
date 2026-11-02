"""Cache: Redis if configured, else in-memory TTL."""
from __future__ import annotations

import json
import time
from typing import Any

from app.config import get_settings

_settings = get_settings()


class MemoryCache:
    """Simple in-memory TTL cache."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if not item:
            return None
        expires, value = item
        if expires < time.time():
            self._data.pop(key, None)
            return None
        return json.loads(value)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._data[key] = (time.time() + ttl, json.dumps(value, ensure_ascii=False))

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def delete_pattern(self, pattern: str) -> None:
        prefix = pattern.replace("*", "")
        for k in list(self._data):
            if k.startswith(prefix):
                self._data.pop(k, None)

    async def get_or_set(self, key: str, ttl: int, factory: Any) -> Any:
        val = await self.get(key)
        if val is not None:
            return val
        val = await factory()
        if val is not None:
            await self.set(key, val, ttl)
        return val

    async def close(self) -> None:
        self._data.clear()


class RedisCache:
    """Redis-backed cache."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        async for k in self._client.scan_iter(match=pattern):
            await self._client.delete(k)

    async def get_or_set(self, key: str, ttl: int, factory: Any) -> Any:
        val = await self.get(key)
        if val is not None:
            return val
        val = await factory()
        if val is not None:
            await self.set(key, val, ttl)
        return val

    async def close(self) -> None:
        await self._client.aclose()


def create_cache() -> MemoryCache | RedisCache:
    if _settings.redis.url:
        return RedisCache(_settings.redis.url)
    return MemoryCache()


def get_cache() -> MemoryCache | RedisCache:
    """Общий кэш-синглтон (сервисы импортируют get_cache())."""
    return cache


cache: MemoryCache | RedisCache = create_cache()


# ─── Redis-клиент для каскадов/квот (с in-memory заглушкой) ─────────────────


class InMemoryRedis:
    """Минимальный in-memory аналог Redis для dev-режима без сервера.

    Поддерживает операции, которые используют QuotaManager,
    CircuitBreaker и ProviderChain.
    """

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._ttl: dict[str, float] = {}

    def _evict(self) -> None:
        now = time.time()
        for key, expires in list(self._ttl.items()):
            if expires <= now:
                self._data.pop(key, None)
                self._ttl.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._evict()
        return self._data.get(key)

    async def set(
        self,
        key: str,
        value: object,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        self._evict()
        if nx and key in self._data:
            return False
        self._data[key] = str(value)
        if ex:
            self._ttl[key] = time.time() + ex
        return True

    async def exists(self, key: str) -> int:
        self._evict()
        return 1 if key in self._data else 0

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._data:
                self._data.pop(key, None)
                self._ttl.pop(key, None)
                deleted += 1
        return deleted

    async def incr(self, key: str) -> int:
        self._evict()
        value = int(self._data.get(key, "0")) + 1
        self._data[key] = str(value)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._data:
            self._ttl[key] = time.time() + seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        self._evict()
        if key not in self._data:
            return -2
        remaining = self._ttl.get(key)
        if remaining is None:
            return -1
        return max(0, int(remaining - time.time()))

    def pipeline(self) -> "_MemoryPipeline":
        return _MemoryPipeline(self)


class _MemoryPipeline:
    """Транзакционная заглушка redis.pipeline()."""

    def __init__(self, redis: InMemoryRedis) -> None:
        self._redis = redis
        self._ops: list[tuple[str, tuple[object, ...]]] = []

    def incr(self, key: str) -> "_MemoryPipeline":
        self._ops.append(("incr", (key,)))
        return self

    def expire(self, key: str, seconds: int) -> "_MemoryPipeline":
        self._ops.append(("expire", (key, seconds)))
        return self

    async def execute(self) -> list[object]:
        results: list[object] = []
        for name, args in self._ops:
            fn = getattr(self._redis, name)
            results.append(await fn(*args))  # type: ignore[arg-type]
        return results


def get_redis() -> InMemoryRedis | Any:
    """Redis-клиент, если настроен, иначе in-memory заглушка.

    Возвращает клиент с decode_responses=True — QuotaManager и
    CircuitBreaker работают со строками.
    """
    url = (get_settings().redis.url or "").strip()
    if not url:
        return InMemoryRedis()
    try:
        import redis.asyncio as aioredis

        return aioredis.from_url(url, decode_responses=True)
    except Exception:
        return InMemoryRedis()


__all__ = [
    "cache",
    "create_cache",
    "get_redis",
    "InMemoryRedis",
    "MemoryCache",
    "RedisCache",
]