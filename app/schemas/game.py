"""Схема игры."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.city import CityDTO


class GameDTO(BaseModel):
    id: int
    mode: str
    score: int = 0


class GameOut(BaseModel):
    """Игра наружу (API/ответы)."""

    id: str
    user_id: int
    mode: str
    status: str
    score: int = 0
    difficulty: str = "easy"
    started_at: datetime | None = None
    finished_at: datetime | None = None


class GameMoveOut(BaseModel):
    """Ход наружу."""

    game_id: str
    move_number: int = 0
    city_name: str
    is_user: bool = True
    points: int = 0


class MoveResult(BaseModel):
    """Результат хода в «Городах» (game_service.make_move)."""

    city: CityDTO
    points: int
    bot_city: CityDTO | None = None
    game_ended: bool = False
    won: bool = False
    next_letter: str | None = None