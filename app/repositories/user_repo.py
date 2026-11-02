"""User repository."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepo


class UserRepo(BaseRepo[User]):
    """User DB operations."""

    model = User

    async def get_by_tg_id(self, tg_id: int, *, with_profile: bool = True) -> User | None:
        """Load user by Telegram ID."""
        stmt = select(User).where(User.tg_id == tg_id)
        if with_profile:
            stmt = stmt.options(selectinload(User.profile))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_with_profile(self, tg_id: int, username: str | None) -> User:
        """Create user + empty profile."""
        from app.models.profile import Profile

        user = User(tg_id=tg_id, username=username)
        user.profile = Profile()
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_locale(self, user: User, locale: str) -> None:
        """Set preferred locale."""
        user.locale = locale
        await self.session.flush()

    async def update_last_seen(self, user: User) -> None:
        """Bump last_seen_at."""
        user.last_seen_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def set_notify(self, user: User, value: bool) -> None:
        """Toggle notifications."""
        user.notify = value
        await self.session.flush()

    async def set_banned(self, user: User, value: bool) -> None:
        """Ban/unban."""
        user.is_banned = value
        await self.session.flush()

    async def list_for_broadcast(self, offset: int, limit: int) -> list[User]:
        """Iterate users in batches."""
        res = await self.session.execute(
            select(User)
            .where(User.is_banned.is_(False))
            .order_by(User.id)
            .offset(offset)
            .limit(limit)
        )
        return list(res.scalars().all())

    async def count_all(self) -> int:
        """Total users."""
        res = await self.session.execute(select(func.count()).select_from(User))
        return int(res.scalar_one())