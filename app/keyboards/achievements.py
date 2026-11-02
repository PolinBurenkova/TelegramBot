"""Клавиатуры раздела достижений."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import CB_MENU_MAIN
from app.keyboards.pagination import pagination_kb

CB_ACH_LIST = "ach:list"
CB_ACH_PAGE_PREFIX = "ach:page"


def achievements_kb(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Список достижений: постраничная навигация и выход в меню."""
    return pagination_kb(
        CB_ACH_PAGE_PREFIX, page, total_pages, back_callback=CB_MENU_MAIN
    )


def achievement_unlocked_kb() -> InlineKeyboardMarkup:
    """Клавиатура под уведомлением о новом достижении."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Все достижения", callback_data=CB_ACH_LIST)],
            [InlineKeyboardButton(text="↩️ В меню", callback_data=CB_MENU_MAIN)],
        ]
    )
