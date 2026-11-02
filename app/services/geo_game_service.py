"""Игровой цикл GeoGuessr."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import XP_FOR_GEO
from app.models.enums import GameStatus, GameType
from app.models.game import Game
from app.repositories.game_repo import GameRepository
from app.repositories.profile_repo import ProfileRepository
from app.services.geo_score import calculate_score, haversine


class GeoGameService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._game_repo = GameRepository(session)
        self._profile_repo = ProfileRepository(session)

    async def start(self, user_id: int) -> Game:
        game = Game(
            user_id=user_id,
            game_type=GameType.GEOGUESSR,
            status=GameStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(game)
        await self._session.flush()
        return game

    async def check_answer(
        self,
        game: Game,
        real_lat: float,
        real_lon: float,
        guess_lat: float,
        guess_lon: float,
    ) -> dict[str, Any]:
        distance = haversine(real_lat, real_lon, guess_lat, guess_lon)
        score = calculate_score(distance)
        game.score += score
        profile = await self._profile_repo.get_by_user(game.user_id)
        if profile is not None:
            await self._profile_repo.add_xp(profile, XP_FOR_GEO)
        await self._session.flush()
        return {"distance_km": distance, "score": score}