"""/profile и /stats."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.user_stats import UserStats

router = Router(name="profile")


@router.message(Command("profile"))
async def cmd_profile(message: Message, session, user) -> None:
    stats = await UserStats(session).get(user.id)
    text = (
        f"👤 <b>{user.first_name or 'Игрок'}</b>\n\n"
        f"⭐ Уровень: <b>{stats['level']}</b>\n"
        f"✨ XP: <b>{stats['xp']}</b>\n"
        f"🎮 Игр: <b>{stats['games']}</b>\n"
        f"🏙 Городов: <b>{stats.get('cities_used', 0)}</b>\n"
        f"🌍 Стран: <b>{stats.get('countries_visited', 0)}</b>"
    )
    await message.answer(text)