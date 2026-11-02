"""Start handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards import main_menu_kb
from app.services.achievement_service import AchievementService
from app.services.user_service import UserService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session, _, **kwargs) -> None:
    users = UserService(session)
    await users.get_or_create(
        message.from_user.id,  # type: ignore[union-attr]
        message.from_user.username if message.from_user else None,  # type: ignore[union-attr]
    )

    ach = AchievementService(session)
    await ach.seed()

    name = (
        message.from_user.first_name  # type: ignore[union-attr]
        if message.from_user and message.from_user.first_name
        else "друг"
    )
    await message.answer(
        _("start.hello", name=name),
        reply_markup=main_menu_kb(_),
    )