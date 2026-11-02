"""Достижения: список с пагинацией."""
from __future__ import annotations

import math
from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.achievements import (
    CB_ACH_PAGE_PREFIX,
    achievements_kb,
)
from app.services.achievement_service import AchievementService

router = Router(name="achievements")

PAGE_SIZE = 5


async def _render(session: Any, user: Any, page: int) -> tuple[str, Any]:
    """Собрать текст страницы достижений и клавиатуру под неё."""
    rows = await AchievementService(session).list_for_user(user)
    total = len(rows)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    unlocked = sum(1 for _, is_unlocked in rows if is_unlocked)

    chunk = rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    lines = [f"🏆 <b>Достижения</b> — {unlocked}/{total} открыто\n"]
    if not chunk:
        lines.append(
            "Пока достижений нет. Загляните позже или начните партию командой /start."
        )
    for achievement, is_unlocked in chunk:
        icon = achievement.icon or "🏅"
        mark = "✅" if is_unlocked else "🔒"
        lines.append(
            f"{mark} {icon} <b>{achievement.title}</b>\n"
            f"   <i>{achievement.description}</i>"
        )
    return "\n".join(lines), achievements_kb(page, total_pages)


async def show_achievements(message: Message, session, user) -> None:
    """Список достижений (первая страница).

    Вызывается из меню (`app.handlers.menu.menu_achievements`), потому что
    reply-кнопка «🏆 Достижения» обрабатывается роутером меню раньше этого.
    """
    text, keyboard = await _render(session, user, 0)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(f"{CB_ACH_PAGE_PREFIX}:"))
async def paginate_achievements(callback: CallbackQuery, session, user) -> None:
    """Перелистывание списка достижений."""
    raw = (callback.data or "").rsplit(":", 1)[-1]
    page = int(raw) if raw.isdigit() else 0
    text, keyboard = await _render(session, user, page)
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
