"""Base FSM states."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BaseStates(StatesGroup):
    """Common cancel state."""

    cancel = State()