"""Главное меню: показ клавиатуры и обработка её кнопок.

Все тексты кнопок из ``app.keyboards.main_menu`` обрабатываются здесь, причём
этот роутер подключается раньше игровых: нажатие «👤 Профиль» во время партии
показывает профиль, а не воспринимается как ход.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.constants import CB_MENU_MAIN
from app.handlers.achievements import show_achievements
from app.handlers.geoguessr import cmd_geo
from app.handlers.help import cmd_help
from app.handlers.leaderboard import cmd_leaderboard
from app.handlers.profile import cmd_profile
from app.handlers.settings import cmd_settings
from app.keyboards import difficulty_kb, main_menu_kb
from app.keyboards.main_menu import (
    BTN_ACHIEVEMENTS,
    BTN_GEO,
    BTN_HELP,
    BTN_LEADERBOARD,
    BTN_PLAY,
    BTN_PROFILE,
    BTN_SETTINGS,
)

router = Router(name="menu")

#: callback_data кнопки «Назад» в инлайн-клавиатурах (app/keyboards/common.py)
CB_BACK = "back"


@router.message(Command("menu"))
async def cmd_menu(message: Message, _) -> None:
    """Показать меню и вернуть reply-клавиатуру, если её свернули."""
    await message.answer(_("menu.title"), reply_markup=main_menu_kb(_))


@router.message(Command("play"))
async def cmd_play(message: Message, _) -> None:
    """Команда /play — то же, что кнопка «🏙 Играть»."""
    await menu_play(message, _)


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, session, user) -> None:
    """Команда /achievements — то же, что кнопка «🏆 Достижения»."""
    await show_achievements(message, session, user)


async def _safe_answer(cb: CallbackQuery, text: str | None = None) -> None:
    """Ответить на callback, не падая при «query is too old»."""
    try:
        await (cb.answer(text) if text is not None else cb.answer())
    except Exception:
        pass


async def _return_to_menu(cb: CallbackQuery, state: FSMContext, _) -> None:
    """Убрать инлайн-кнопки и отправить меню с постоянной клавиатурой.

    Reply-клавиатуру нельзя прикрепить к ``edit_text`` (Telegram принимает там
    только inline-разметку), поэтому старый инлайн убираем, а меню приходит
    новым сообщением.
    """
    await state.clear()
    if cb.message is not None:
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await cb.message.answer(_("menu.title"), reply_markup=main_menu_kb(_))
    await _safe_answer(cb)


@router.callback_query(F.data == CB_MENU_MAIN)
async def back_to_menu(cb: CallbackQuery, state: FSMContext, _) -> None:
    """«🏠 В меню» / «↩️ Назад» из инлайн-экранов."""
    await _return_to_menu(cb, state, _)


@router.callback_query(F.data == CB_BACK)
async def back_button(cb: CallbackQuery, state: FSMContext, _) -> None:
    """Кнопка «⬅️ Назад» из `back_kb` (раньше не была обработана)."""
    await _return_to_menu(cb, state, _)


@router.message(F.text == BTN_PLAY)
async def menu_play(message: Message, _) -> None:
    """«Играть» → выбор сложности для режима «Города»."""
    await message.answer(
        "🎯 Выберите сложность", reply_markup=difficulty_kb("cities", _)
    )


@router.message(F.text == BTN_GEO)
async def menu_geo(message: Message, state: FSMContext, session, user) -> None:
    """«GeoGuessr» → старт раунда (та же логика, что у /geo)."""
    await cmd_geo(message, state, session, user)


@router.message(F.text == BTN_PROFILE)
async def menu_profile(message: Message, session, user) -> None:
    """«Профиль» → статистика игрока."""
    await cmd_profile(message, session, user)


@router.message(F.text == BTN_ACHIEVEMENTS)
async def menu_achievements(message: Message, session, user) -> None:
    """«Достижения» → список достижений с пагинацией."""
    await show_achievements(message, session, user)


@router.message(F.text == BTN_LEADERBOARD)
async def menu_leaderboard(message: Message, session) -> None:
    """«Лидерборд» → топ игроков."""
    await cmd_leaderboard(message, session)


@router.message(F.text == BTN_SETTINGS)
async def menu_settings(message: Message, user) -> None:
    """«Настройки» → экран настроек."""
    await cmd_settings(message, user)


@router.message(F.text == BTN_HELP)
async def menu_help(message: Message, _) -> None:
    """«Помощь» → справка."""
    await cmd_help(message, _)
