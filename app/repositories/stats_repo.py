"""Aggregated stats queries."""
from __future__ import annotations

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.profile import Profile
from app.models.user import User


class StatsRepo:
    """Complex aggregate queries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def top_users(self, limit: int = 10) -> list[tuple[User, Profile]]:
        """Leaderboard by total score (cities + geo)."""
        total = Profile.cities_score + Profile.geo_score
        res = await self.session.execute(
            select(User, Profile)
            .join(Profile, Profile.user_id == User.id)
            .order_by(total.desc())
            .limit(limit)
        )
        return [(u, p) for u, p in res.all()]

    async def win_rate(self, user_id: int) -> float:
        """Win rate 0..1."""
        res = await self.session.execute(
            select(
                func.count(Game.id),
                func.sum(Game.won.cast(Integer)),
            ).where(Game.user_id == user_id, Game.status == "finished")
        )
        total, wins = res.one()
        if not total:
            return 0.0
        return float(wins or 0) / float(total)

    async def avg_cities_per_game(self, user_id: int) -> float:
        """Average cities per finished game.

        ``Game.cities_count`` — Python-property (алиас ``moves_count``), в SQL его
        подставлять нельзя: фильтруем по реальной колонке.
        """
        res = await self.session.execute(
            select(func.avg(Game.moves_count)).where(
                Game.user_id == user_id, Game.status == "finished"
            )
        )
        return float(res.scalar_one() or 0.0)