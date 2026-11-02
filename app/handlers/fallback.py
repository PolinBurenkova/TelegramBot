"""Fallback handler — must be last in router."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from app.keyboards import main_menu_kb

router = Router()


@router.message()
async def fallback(message: Message, _) -> None:
    # Возвращаем reply-клавиатуру: на мобильном клиенте она остаётся под полем
    # ввода, и пользователю не нужно снова набирать /start.
    await message.answer("🤔 Не понял. Используйте меню.", reply_markup=main_menu_kb(_))
