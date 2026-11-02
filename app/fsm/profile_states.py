"""FSM для профиля."""

from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    confirm_reset = State()