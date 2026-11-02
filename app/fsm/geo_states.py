"""FSM для GeoGuessr."""

from aiogram.fsm.state import State, StatesGroup


class GeoGame(StatesGroup):
    waiting_answer = State()
    showing_result = State()


# Совместимый алиас (fsm/__init__ импортирует GeoStates)
GeoStates = GeoGame