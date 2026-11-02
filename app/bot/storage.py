"""FSM storage: Redis if configured, else Memory."""
from __future__ import annotations

from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Settings, get_settings


def create_storage(settings: Settings | None = None) -> BaseStorage:
    """Return RedisStorage if Redis configured and reachable, else MemoryStorage."""
    if settings is None:
        settings = get_settings()

    if settings.redis.url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            return RedisStorage.from_url(
                settings.redis.url,
                state_ttl=settings.redis.state_ttl,
                data_ttl=settings.redis.data_ttl,
            )
        except Exception:
            pass
    return MemoryStorage()