"""Admin handlers."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.filters.is_admin import IsAdmin
from app.repositories.user_repo import UserRepo

router = Router()


@router.message(Command("stats_bot"), IsAdmin())
async def cmd_stats_bot(message: Message, session) -> None:
    users = UserRepo(session)
    total = await users.count_all()
    await message.answer(f"👥 Всего пользователей: {total}")