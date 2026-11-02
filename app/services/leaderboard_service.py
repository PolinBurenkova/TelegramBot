"""Leaderboard."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats_repo import StatsRepo
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardPage


class LeaderboardService:
    """Top-N leaderboard."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.stats = StatsRepo(session)

    async def top(self, limit: int = 10) -> list[dict[str, object]]:
        """Топ игроков: список словарей для хендлера лидерборда."""
        rows = await self.stats.top_users(limit)
        return [
            {
                "rank": i + 1,
                "first_name": None,
                "username": u.username or f"user_{u.tg_id}",
                "telegram_id": u.tg_id,
                "xp": p.xp,
                "level": p.level,
            }
            for i, (u, p) in enumerate(rows)
        ]