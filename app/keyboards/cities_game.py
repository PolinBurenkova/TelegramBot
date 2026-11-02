"""Клавиатуры игры «Города»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import CB_MENU_CITIES, CB_MENU_MAIN, CB_SURRENDER


def game_kb(_: object | None = None) -> InlineKeyboardMarkup:
    """Меню активной игры. Аргумент _ — translator, не используется."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Сдаться", callback_data=CB_SURRENDER)]
        ]
    )


def after_game_kb(_: object | None = None) -> InlineKeyboardMarkup:
    """Меню после завершения игры."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Играть снова", callback_data=CB_MENU_CITIES
                )
            ],
            [InlineKeyboardButton(text="🏠 В меню", callback_data=CB_MENU_MAIN)],
        ]
    )
