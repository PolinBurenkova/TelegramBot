"""/settings."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.settings import confirm_reset_kb, difficulty_kb, settings_kb
from app.services.settings_service import SettingsService

router = Router(name="settings")


@router.message(Command("settings"))
async def cmd_settings(message: Message, user) -> None:
    text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"Сложность: <b>{user.difficulty}</b>\n"
        f"Язык: <b>{user.language}</b>\n"
        f"Уведомления: {'вкл' if user.notify else 'выкл'}"
    )
    await message.answer(text, reply_markup=settings_kb())


@router.callback_query(F.data == "settings:difficulty")
async def show_difficulty(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Выберите сложность:", reply_markup=difficulty_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("diff:"))
async def set_difficulty(callback: CallbackQuery, session, user) -> None:
    _, value = callback.data.split(":", 1)
    await SettingsService(session).set_difficulty(user, value)
    if callback.message:
        await callback.message.edit_text(f"✅ Сложность: {value}")
    await callback.answer()


@router.callback_query(F.data == "settings:reset")
async def ask_reset(callback: CallbackQuery) -> None:
    """Спросить подтверждение сброса прогресса."""
    if callback.message:
        await callback.message.edit_text(
            "⚠️ Точно сбросить весь прогресс?",
            reply_markup=confirm_reset_kb(),
        )
    await callback.answer()


@router.callback_query(F.data == "settings:notifications")
async def toggle_notify(callback: CallbackQuery, session, user) -> None:
    """Переключить уведомления."""
    from app.services.user_service import UserService

    new_value = await UserService(session).toggle_notify(user)
    if callback.message:
        await callback.message.edit_text(
            f"🔔 Уведомления: {'вкл' if new_value else 'выкл'}",
            reply_markup=settings_kb(new_value),
        )
    await callback.answer()