"""Клавиатуры админ-панели."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import CB_MENU_MAIN

CB_ADMIN_STATS = "admin:stats"
CB_ADMIN_USERS = "admin:users"
CB_ADMIN_CACHE = "admin:cache"


def admin_kb() -> InlineKeyboardMarkup:
    """Главное меню администратора."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data=CB_ADMIN_STATS)],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data=CB_ADMIN_USERS)],
            [InlineKeyboardButton(text="🔄 Обновить кэш", callback_data=CB_ADMIN_CACHE)],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=CB_MENU_MAIN)],
        ]
    )
