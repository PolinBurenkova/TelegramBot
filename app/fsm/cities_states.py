"""Cities game states."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CitiesStates(StatesGroup):
    """Cities game FSM."""

    waiting_city = State()
    game_over = State()