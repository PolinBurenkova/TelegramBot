"""Главное меню: постоянная reply-клавиатура.

Reply-клавиатура (в отличие от inline) рисуется клиентом под полем ввода и
одинаково доступна на десктопе и в мобильном приложении. `is_persistent=True`
не даёт ей сворачиваться при повторном открытии чата, `input_field_placeholder`
показывает подсказку в строке ввода на мобильном.
"""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_PLAY = "🏙 Играть"
BTN_GEO = "🌍 GeoGuessr"
BTN_PROFILE = "👤 Профиль"
BTN_ACHIEVEMENTS = "🏆 Достижения"
BTN_LEADERBOARD = "📊 Лидерборд"
BTN_SETTINGS = "⚙️ Настройки"
BTN_HELP = "❓ Помощь"

#: Тексты кнопок меню — по ним же строится фильтр хендлеров.
MAIN_MENU_TEXTS: frozenset[str] = frozenset(
    {
        BTN_PLAY,
        BTN_GEO,
        BTN_PROFILE,
        BTN_ACHIEVEMENTS,
        BTN_LEADERBOARD,
        BTN_SETTINGS,
        BTN_HELP,
    }
)


def main_menu_kb(_: object | None = None) -> ReplyKeyboardMarkup:
    """Главное меню (reply). Аргумент _ — translator, не используется."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PLAY), KeyboardButton(text=BTN_GEO)],
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_ACHIEVEMENTS)],
            [KeyboardButton(text=BTN_LEADERBOARD), KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите раздел меню",
    )
