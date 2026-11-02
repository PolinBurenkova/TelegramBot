"""Клавиатуры GeoGuessr."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def geo_kb(panorama_url: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if panorama_url:
        rows.append(
            [InlineKeyboardButton(text="🗺 Открыть панораму", url=panorama_url)]
        )
    rows.append(
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="geo:skip")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)