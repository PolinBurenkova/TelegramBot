"""Общие клавиатуры."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def back_kb(_: object | None = None) -> InlineKeyboardMarkup:
    """Кнопка «Назад». Аргумент _ — translator, не используется."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]]
    )


def cancel_kb(_: object | None = None) -> InlineKeyboardMarkup:
    """Кнопка «Отмена». Аргумент _ — translator, не используется."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    )