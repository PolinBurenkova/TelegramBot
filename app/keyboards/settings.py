"""Клавиатуры настроек."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import CB_RESET_CANCEL, CB_RESET_CONFIRM


def settings_kb(
    notify: bool | None = None, _: object | None = None
) -> InlineKeyboardMarkup:
    """Меню настроек; notify — текущее состояние уведомлений."""
    notify = True if notify is None else bool(notify)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎚 Сложность", callback_data="settings:difficulty"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔔 Уведомления: {'вкл' if notify else 'выкл'}",
                    callback_data="settings:notifications",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Сбросить прогресс", callback_data="settings:reset"
                )
            ],
        ]
    )


def confirm_reset_kb() -> InlineKeyboardMarkup:
    """Подтверждение сброса прогресса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, сбросить", callback_data=CB_RESET_CONFIRM
                )
            ],
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=CB_RESET_CANCEL)],
        ]
    )


def difficulty_kb(
    game_type: str | None = None, _: object | None = None
) -> InlineKeyboardMarkup:
    """Сложность: diff:<level> (настройки) или diff:<game>:<level> (игра)."""
    rows = []
    for level, title in (
        ("easy", "🟢 Легко"),
        ("medium", "🟡 Средне"),
        ("hard", "🔴 Сложно"),
    ):
        data = f"diff:{game_type}:{level}" if game_type else f"diff:{level}"
        rows.append([InlineKeyboardButton(text=title, callback_data=data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
