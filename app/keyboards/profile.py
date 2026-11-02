"""Клавиатуры профиля."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Достижения", callback_data="profile:ach")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="profile:stats")],
        ]
    )