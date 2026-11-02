"""/leaderboard."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.leaderboard_service import LeaderboardService

router = Router(name="leaderboard")


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message, session) -> None:
    top = await LeaderboardService(session).top()
    if not top:
        await message.answer("🏆 Пока никого нет.")
        return
    lines = ["🏆 <b>Топ-10 игроков</b>\n"]
    for i, row in enumerate(top, start=1):
        name = row["first_name"] or row["username"] or f"id{row['telegram_id']}"
        lines.append(f"{i}. {name} — {row['xp']} XP (ур. {row['level']})")
    await message.answer("\n".join(lines))