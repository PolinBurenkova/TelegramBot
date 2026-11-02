""""Game and GameMove repositories."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.models.enums import GameStatus
from app.models.game import Game
from app.models.game_move import GameMove
from app.repositories.base import BaseRepo


class GameRepo(BaseRepo[Game]):
    """Game DB operations."""

    model = Game

    async def get_active(self, user_id: int, game_type: str = "cities") -> Game | None:
        """Find active game for user (последняя незакрытая, если их несколько)."""
        res = await self.session.execute(
            select(Game)
            .where(
                Game.user_id == user_id,
                Game.game_type == game_type,
                Game.status == GameStatus.ACTIVE.value,
            )
            .order_by(Game.started_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def create_active(
        self,
        user_id: int,
        game_type: str = "cities",
        difficulty: str = "easy",
        meta: dict[str, Any] | None = None,
    ) -> Game:
        """Create active game."""
        return await self.create(
            user_id=user_id,
            game_type=game_type,
            difficulty=difficulty,
            status=GameStatus.ACTIVE.value,
            meta=meta,
        )

    async def finish(self, game: Game, *, won: bool, score: int | None = None) -> None:
        """Mark game finished."""
        game.status = GameStatus.FINISHED.value
        game.finished_at = datetime.now(timezone.utc)
        game.won = won
        if score is not None:
            game.score = score
        await self.session.flush()

    async def list_by_user(
        self, user_id: int, page: int = 0, size: int = 10
    ) -> list[Game]:
        """Paginated history."""
        res = await self.session.execute(
            select(Game)
            .where(Game.user_id == user_id)
            .order_by(Game.started_at.desc())
            .offset(page * size)
            .limit(size)
        )
        return list(res.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """Total games for user."""
        res = await self.session.execute(
            select(func.count()).select_from(Game).where(Game.user_id == user_id)
        )
        return int(res.scalar_one())


class MoveRepo(BaseRepo[GameMove]):
    """GameMove DB operations."""

    model = GameMove

    async def last_move(self, game_id: int) -> GameMove | None:
        """Latest move in game."""
        res = await self.session.execute(
            select(GameMove)
            .where(GameMove.game_id == game_id)
            .order_by(GameMove.move_number.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def next_move_number(self, game_id: int) -> int:
        """Next move number."""
        last = await self.last_move(game_id)
        return (last.move_number + 1) if last else 1

    async def create_move(
        self,
        game_id: UUID | str,
        city_name: str,
        *,
        is_user: bool = True,
        points: int = 0,
        payload: dict[str, Any] | None = None,
    ) -> GameMove:
        """Append a move."""
        from app.utils.validators import normalize_city

        number = await self.next_move_number(game_id)
        return await self.create(
            game_id=game_id,
            move_number=number,
            city_name=city_name,
            normalized_name=normalize_city(city_name),
            is_user=is_user,
            points=points,
            payload=payload,
        )

    async def list_by_game(self, game_id: int) -> list[GameMove]:
        """All moves ordered."""
        res = await self.session.execute(
            select(GameMove)
            .where(GameMove.game_id == game_id)
            .order_by(GameMove.move_number)
        )
        return list(res.scalars().all())


# Совместимость: geo_game_service импортирует GameRepository
GameRepository = GameRepo