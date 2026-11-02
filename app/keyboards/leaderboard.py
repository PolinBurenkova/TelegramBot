"""Клавиатуры лидерборда."""

from aiogram.types import InlineKeyboardMarkup


def leaderboard_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])