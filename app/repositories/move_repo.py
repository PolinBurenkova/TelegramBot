"""Репозиторий ходов."""

from app.models.game_move import GameMove
from app.repositories.base import BaseRepository


class MoveRepository(BaseRepository[GameMove]):
    """Совместимый алиас; канонический класс — ``app.repositories.game_repo.MoveRepo``."""

    model = GameMove