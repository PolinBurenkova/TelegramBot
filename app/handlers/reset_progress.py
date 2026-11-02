"""Reset progress handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.constants import CB_RESET_CANCEL, CB_RESET_CONFIRM
from app.keyboards import back_kb, settings_kb
from app.services.user_service import UserService

router = Router()


@router.callback_query(F.data == CB_RESET_CONFIRM)
async def do_reset(cb: CallbackQuery, session, _, user) -> None:
    users = UserService(session)
    await users.reset_progress(user)
    if cb.message:
        await cb.message.edit_text(_("settings.reset_done"), reply_markup=back_kb(_))
    await cb.answer()


@router.callback_query(F.data == CB_RESET_CANCEL)
async def cancel_reset(cb: CallbackQuery, _, user) -> None:
    if cb.message:
        await cb.message.edit_text(
            _("settings.title"),
            reply_markup=settings_kb(user.notify, _),
        )
    await cb.answer()