"""ApiCache repository."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.models.api_cache import ApiCache
from app.repositories.base import BaseRepo


class ApiCacheRepo(BaseRepo[ApiCache]):
    """ApiCache DB operations."""

    model = ApiCache

    async def get_fresh(self, key: str) -> dict[str, Any] | None:
        """Get payload if not expired."""
        row = await self.session.get(ApiCache, key)
        if not row:
            return None
        if row.expires_at < datetime.now(timezone.utc):
            return None
        return row.value

    async def set(
        self,
        key: str,
        provider: str,
        payload: dict[str, Any],
        ttl: int,
    ) -> None:
        """Upsert entry with TTL."""
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        existing = await self.session.get(ApiCache, key)
        if existing:
            existing.provider = provider
            existing.value = payload
            existing.expires_at = expires
        else:
            await self.create(
                key=key, provider=provider, value=payload, expires_at=expires
            )
        await self.session.flush()

    async def purge_expired(self) -> int:
        """Delete expired rows. Returns count."""
        now = datetime.now(timezone.utc)
        rows = await self.session.execute(
            select(ApiCache).where(ApiCache.expires_at < now)
        )
        count = 0
        for row in rows.scalars():
            await self.session.delete(row)
            count += 1
        await self.session.flush()
        return count