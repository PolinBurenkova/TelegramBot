"""Пагинация списков: общая инлайн-клавиатура."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def clamp_page(page: int, total_pages: int) -> int:
    """Привести номер страницы к диапазону [0, total_pages - 1]."""
    total = max(1, int(total_pages))
    return max(0, min(int(page), total - 1))


def pagination_kb(
    prefix: str,
    page: int,
    total_pages: int,
    *,
    back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура «◀️ N/M ▶️» для списка с ``prefix`` в callback_data.

    callback_data стрелок — ``<prefix>:<page>``; кнопка-счётчик — ``noop``.
    Стрелка на границе списка не показывается, поэтому на одной странице
    остаётся только счётчик.
    """
    total = max(1, int(total_pages))
    current = clamp_page(page, total)
    row: list[InlineKeyboardButton] = []
    if current > 0:
        row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:{current - 1}")
        )
    row.append(
        InlineKeyboardButton(text=f"{current + 1}/{total}", callback_data="noop")
    )
    if current + 1 < total:
        row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:{current + 1}")
        )

    rows: list[list[InlineKeyboardButton]] = [row]
    if back_callback:
        rows.append(
            [InlineKeyboardButton(text="↩️ Назад", callback_data=back_callback)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
