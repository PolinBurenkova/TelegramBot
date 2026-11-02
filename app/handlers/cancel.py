"""Cancel handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.constants import CB_CANCEL
from app.keyboards import main_menu_kb

router = Router()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, _) -> None:
    await state.clear()
    await message.answer(_("menu.title"), reply_markup=main_menu_kb(_))


@router.callback_query(F.data == CB_CANCEL)
async def cb_cancel(cb: CallbackQuery, state: FSMContext, _) -> None:
    await state.clear()
    if cb.message:
        # Reply-клавиатуру нельзя прикрепить к edit_text — убираем инлайн и
        # отправляем меню отдельным сообщением.
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await cb.message.answer(_("menu.title"), reply_markup=main_menu_kb(_))
    await cb.answer()