"""История игр."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game


class GameHistory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def last_games(self, user_id: int, limit: int = 10) -> list[Game]:
        result = await self._session.execute(
            select(Game)
            .where(Game.user_id == user_id)
            .order_by(Game.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())