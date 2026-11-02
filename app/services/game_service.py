"""Cities game logic."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import WIN_BONUS
from app.exceptions import CityAlreadyUsed, CityNotFound, GameNotFound, WrongLetter
from app.models.city import City
from app.models.enums import GameStatus
from app.models.game import Game
from app.models.user import User
from app.repositories.game_repo import GameRepo, MoveRepo
from app.repositories.user_used_city_repo import UserUsedCityRepo
from app.schemas.game import MoveResult
from app.services.city_service import CityService
from app.services.external.registry import ExternalRegistry
from app.services.score_service import ScoreService
from app.utils.validators import first_letter, last_letter, normalize_city


class GameService:
    """Cities game orchestration."""

    def __init__(
        self,
        session: AsyncSession,
        external: ExternalRegistry | None = None,
    ) -> None:
        self.session = session
        self.games = GameRepo(session)
        self.moves = MoveRepo(session)
        self.used = UserUsedCityRepo(session)
        self.city_service = CityService(session, external)

    async def start_game(self, user: User, difficulty: str = "easy") -> Game | None:
        active = await self.games.get_active(user.id)
        if active:
            await self.games.finish(active, won=False)

        # Стартовый город — любой из справочника: порог по населению снят.
        starter = await self.city_service.random()
        if not starter:
            return None

        game = await self.games.create_active(
            user_id=user.id,
            game_type="cities",
            difficulty=difficulty,
            meta={"start_letter": first_letter(starter.name)},
        )
        await self.moves.create_move(
            game.id, starter.name, is_user=False, points=0
        )
        # moves_count — общее число ходов партии (и стартовый город тоже ход)
        game.moves_count = 1
        await self.used.add(user.id, starter.name_norm, game.id)
        return game

    async def make_move(
        self, game: Game, user: User, city_name: str
    ) -> MoveResult:
        norm = normalize_city(city_name)

        if await self.used.exists(user.id, norm, game.id):
            raise CityAlreadyUsed()

        last_move = await self.moves.last_move(game.id)
        if not last_move:
            raise GameNotFound("Нет предыдущего хода")

        required = last_letter(last_move.city_name)
        if first_letter(norm) != required:
            raise WrongLetter(f"Нужна буква «{required.upper()}»")

        city = await self.city_service.find(city_name)
        if not city:
            raise CityNotFound()

        points = ScoreService.city_points(city.name, game.difficulty)
        await self.moves.create_move(
            game.id, city.name, is_user=True, points=points
        )
        await self.used.add(user.id, city.name_norm, game.id)
        game.score += points
        game.moves_count += 1

        bot_city = await self._pick_bot_city(game, last_letter(city.name), user)
        if not bot_city:
            game.score += WIN_BONUS
            await self.games.finish(game, won=True)
            return MoveResult(
                city=self.city_service.to_out(city),
                points=points,
                bot_city=None,
                game_ended=True,
                won=True,
                next_letter=None,
            )

        await self.moves.create_move(
            game.id, bot_city.name, is_user=False, points=0
        )
        await self.used.add(user.id, bot_city.name_norm, game.id)
        game.moves_count += 1

        return MoveResult(
            city=self.city_service.to_out(city),
            points=points,
            bot_city=self.city_service.to_out(bot_city),
            game_ended=False,
            won=False,
            next_letter=last_letter(bot_city.name),
        )

    async def _pick_bot_city(
        self, game: Game, letter: str, user: User
    ) -> City | None:
        used_norms = set(await self.used.list_by_game(game.id))
        candidates = await self.city_service.repo.list_starting_with(letter, limit=200)
        candidates = [c for c in candidates if c.name_norm not in used_norms]
        if not candidates:
            return None
        candidates.sort(key=lambda c: c.population or 0, reverse=True)
        return candidates[0]

    async def surrender(self, game: Game) -> int:
        await self.games.finish(game, won=False)
        return game.score

    async def timeout(self, game: Game) -> int:
        """Завершить партию по истечении времени на ход (статус ``timeout``)."""
        game.status = GameStatus.TIMEOUT.value
        game.finished_at = datetime.now(timezone.utc)
        game.won = False
        await self.session.flush()
        return game.score

    async def get_active(self, user: User) -> Game | None:
        return await self.games.get_active(user.id)