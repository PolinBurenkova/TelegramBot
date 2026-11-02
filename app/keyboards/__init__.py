"""Пакет клавиатур — реэкспорт билдеров для хендлеров."""
from app.keyboards.achievements import achievement_unlocked_kb, achievements_kb
from app.keyboards.admin import admin_kb
from app.keyboards.cities_game import after_game_kb, game_kb
from app.keyboards.common import back_kb, cancel_kb
from app.keyboards.difficulty import difficulty_kb
from app.keyboards.main_menu import main_menu_kb
from app.keyboards.pagination import clamp_page, pagination_kb
from app.keyboards.settings import confirm_reset_kb, settings_kb

__all__ = [
    "achievement_unlocked_kb",
    "achievements_kb",
    "admin_kb",
    "after_game_kb",
    "back_kb",
    "cancel_kb",
    "clamp_page",
    "confirm_reset_kb",
    "difficulty_kb",
    "game_kb",
    "main_menu_kb",
    "pagination_kb",
    "settings_kb",
]
