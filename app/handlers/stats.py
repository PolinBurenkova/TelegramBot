"""Stats handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.constants import CB_MENU_STATS
from app.keyboards import back_kb
from app.repositories.stats_repo import StatsRepo

router = Router()


@router.callback_query(F.data == CB_MENU_STATS)
async def show_stats(cb: CallbackQuery, session, _, user) -> None:
    stats = StatsRepo(session)
    winrate = await stats.win_rate(user.id)
    avg = await stats.avg_cities_per_game(user.id)

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"🎮 Игр: {user.profile.total_games}\n"
        f"🏆 Побед: {user.profile.total_wins}\n"
        f"📈 Winrate: {winrate * 100:.0f}%\n"
        f"🏙 Среднее городов за игру: {avg:.1f}"
    )
    if cb.message:
        await cb.message.edit_text(text, reply_markup=back_kb(_))
    await cb.answer()