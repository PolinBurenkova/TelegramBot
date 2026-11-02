"""Уведомления пользователя: создание, чтение, отметка о прочтении."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationService:
    """Тонкий сервис поверх таблицы ``notifications``."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: int, title: str, body: str | None = None
    ) -> Notification:
        """Создать уведомление (body по умолчанию совпадает с title)."""
        notification = Notification(
            user_id=user_id,
            title=title[:150],
            body=(body or title),
            is_read=False,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def list_for_user(
        self, user_id: int, limit: int = 20, *, unread_only: bool = False
    ) -> list[Notification]:
        """Последние уведомления пользователя (свежие первыми)."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(max(1, limit))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(self, notification_id: int, user_id: int | None = None) -> bool:
        """Пометить уведомление прочитанным; False — не найдено/чужое."""
        notification = await self.session.get(Notification, notification_id)
        if notification is None:
            return False
        if user_id is not None and notification.user_id != user_id:
            return False
        notification.is_read = True
        await self.session.flush()
        return True

    async def mark_all_read(self, user_id: int) -> int:
        """Пометить все уведомления пользователя прочитанными."""
        rows = await self.list_for_user(user_id, limit=500, unread_only=True)
        for row in rows:
            row.is_read = True
        if rows:
            await self.session.flush()
        return len(rows)

    async def unread_count(self, user_id: int) -> int:
        """Количество непрочитанных уведомлений."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return int(result.scalar_one() or 0)
