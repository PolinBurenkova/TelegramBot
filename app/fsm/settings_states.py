"""FSM для настроек."""

from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    difficulty = State()
    language = State()
    notifications = State()