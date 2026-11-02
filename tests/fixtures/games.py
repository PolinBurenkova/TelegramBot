# tests/fixtures/games.py
"""Фабрики тестовых данных игровых сессий.

Поля соответствуют реальной модели `app.models.game.Game`:
id (UUID, default uuid4), user_id (FK users.id), game_type, status,
score, moves_count, started_at, finished_at, difficulty, meta, won.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models import Game, GameStatus, GameType

DEFAULT_GAME_USER_ID = 1


def game_data(user_id: int = DEFAULT_GAME_USER_ID, **overrides: Any) -> dict[str, Any]:
    """Данные игровой сессии для `Game(**game_data(user_id))`."""
    data: dict[str, Any] = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "game_type": GameType.CITIES,
        "status": GameStatus.ACTIVE,
        "score": 0,
        "moves_count": 0,
        "started_at": None,
        "finished_at": None,
        "difficulty": "easy",
        "meta": None,
        "won": False,
    }
    data.update(overrides)
    return data


def make_game(user_id: int = DEFAULT_GAME_USER_ID, **overrides: Any) -> Game:
    """Экземпляр `Game` (не сохранённый в БД)."""
    return Game(**game_data(user_id, **overrides))


__all__ = ["DEFAULT_GAME_USER_ID", "game_data", "make_game"]
