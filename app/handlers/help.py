"""Help handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.constants import CB_MENU_HELP
from app.keyboards import back_kb

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message, _) -> None:
    await message.answer(_("help.text"), reply_markup=back_kb(_))


@router.callback_query(F.data == CB_MENU_HELP)
async def cb_help(cb: CallbackQuery, _) -> None:
    if cb.message:
        await cb.message.edit_text(_("help.text"), reply_markup=back_kb(_))
    await cb.answer()