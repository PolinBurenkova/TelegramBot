"""Cities game handler."""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from app.config import get_settings
from app.constants import CB_DIFFICULTY_PREFIX, CB_MENU_CITIES, CB_SURRENDER
from app.database import async_session_factory
from app.exceptions import GameError
from app.fsm.cities_states import CitiesStates
from app.keyboards import after_game_kb, difficulty_kb, game_kb, main_menu_kb
from app.models.enums import GameStatus
from app.models.game import Game
from app.services.achievement_service import AchievementService
from app.services.game_service import GameService
from app.services.user_service import UserService
from app.utils.validators import is_valid_city_input, last_letter

router = Router()

#: Активные таймеры хода: telegram id пользователя → задача.
_timers: dict[int, asyncio.Task[None]] = {}


def move_timeout_seconds() -> int:
    """Сколько секунд даётся на ход (0 — без ограничения)."""
    return max(0, int(get_settings().move_timeout))


def _cancel_timer(tg_id: int) -> None:
    """Отменить запланированный таймаут хода (если есть)."""
    task = _timers.pop(tg_id, None)
    if task is not None and not task.done():
        task.cancel()


def _schedule_timer(
    bot: Any,
    chat_id: int,
    tg_id: int,
    game_id: Any,
    turn: int,
    state: FSMContext,
    seconds: int,
    tr: Callable[..., str],
) -> None:
    """Завершить партию, если игрок не ответил за ``seconds``.

    Таймер сверяет номер хода из FSM: если игрок успел ответить, `turn`
    изменится и старый таймер ничего не сделает.
    """
    _cancel_timer(tg_id)
    if seconds <= 0:
        return

    async def _runner() -> None:
        current = asyncio.current_task()
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return
        try:
            data = await state.get_data()
            if data.get("turn") != turn:
                return
            score = 0
            async with async_session_factory() as session:
                game = await session.get(Game, game_id)
                if game is None or game.status != GameStatus.ACTIVE.value:
                    return
                score = await GameService(session).timeout(game)
                await session.commit()
            await state.clear()
            await bot.send_message(
                chat_id,
                tr("game.timeout", score=score),
                reply_markup=main_menu_kb(tr),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — фоновой задаче нельзя падать молча
            logger.warning("move timer failed: {}", exc)
        finally:
            # Не затираем запись нового таймера того же игрока: снимаем только
            # свою (иначе отменённая задача удалила бы свежую).
            if _timers.get(tg_id) is current:
                _timers.pop(tg_id, None)

    _timers[tg_id] = asyncio.create_task(_runner())


async def _arm_timer(
    bot: Any,
    chat_id: int,
    tg_id: int,
    game_id: Any,
    state: FSMContext,
    tr: Callable[..., str],
) -> int:
    """Запустить таймер на текущий ход; возвращает длительность в секундах."""
    seconds = move_timeout_seconds()
    data = await state.get_data()
    turn = int(data.get("turn", 0)) + 1
    await state.update_data(turn=turn, deadline=time.time() + seconds)
    _schedule_timer(bot, chat_id, tg_id, game_id, turn, state, seconds, tr)
    return seconds


async def _expire_if_late(
    message: Message,
    state: FSMContext,
    session: Any,
    tr: Callable[..., str],
) -> bool:
    """Если время на ход истекло — завершить партию и ответить игроку."""
    data = await state.get_data()
    deadline = data.get("deadline")
    if not deadline or time.time() <= float(deadline):
        return False

    game_id = data.get("game_id")
    score = 0
    if game_id:
        game = await session.get(Game, game_id)
        if game is not None and game.status == GameStatus.ACTIVE.value:
            score = await GameService(session).timeout(game)
            await session.commit()
    if message.from_user is not None:
        _cancel_timer(message.from_user.id)
    await state.clear()
    await message.answer(tr("game.timeout", score=score), reply_markup=main_menu_kb(tr))
    return True


@router.callback_query(F.data == CB_MENU_CITIES)
async def choose_difficulty(cb: CallbackQuery, _) -> None:
    if cb.message:
        await cb.message.edit_text(
            "🎯 Выберите сложность",
            reply_markup=difficulty_kb("cities", _),
        )
    await cb.answer()


@router.callback_query(F.data.startswith(f"{CB_DIFFICULTY_PREFIX}cities:"))
async def start_cities(
    cb: CallbackQuery, state: FSMContext, session, _, external
) -> None:
    difficulty = (cb.data or "").split(":")[-1] or "easy"

    users = UserService(session)
    user = await users.get_or_create(cb.from_user.id, cb.from_user.username)  # type: ignore[union-attr]

    games = GameService(session, external)
    game = await games.start_game(user, difficulty)
    if not game:
        if cb.message:
            await cb.message.answer("⚠️ Не удалось начать игру. Попробуйте позже.")
        await cb.answer()
        return

    last = await games.moves.last_move(game.id)
    await state.update_data(game_id=game.id, user_id=user.id)
    await state.set_state(CitiesStates.waiting_city)

    city_name = last.city_name if last else "Москва"
    letter = last_letter(city_name)
    seconds = await _arm_timer(
        cb.bot, cb.message.chat.id if cb.message else cb.from_user.id,
        cb.from_user.id, game.id, state, _,
    )

    text = _(
        "game.started",
        city=city_name,
        country="—",
        letter=letter.upper(),
    )
    if seconds > 0:
        text = f"{text}\n\n{_('game.timer', seconds=seconds)}"
    if cb.message:
        await cb.message.edit_text(text, reply_markup=game_kb(_))
    await cb.answer()


@router.message(CitiesStates.waiting_city, F.text)
async def handle_city(message: Message, state: FSMContext, session, _, external) -> None:
    text = (message.text or "").strip()

    if not is_valid_city_input(text):
        await message.answer(_("game.bad_input"))
        return

    data = await state.get_data()
    game_id = data.get("game_id")
    if not game_id:
        await message.answer("Игра не найдена. /start")
        await state.clear()
        return

    if await _expire_if_late(message, state, session, _):
        return

    users = UserService(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.username)  # type: ignore[union-attr]

    games = GameService(session, external)
    game = await session.get(Game, game_id)
    if not game or game.status != GameStatus.ACTIVE.value:
        await message.answer("Игра завершена. /start")
        await state.clear()
        return

    try:
        result = await games.make_move(game, user, text)
    except GameError as e:
        await message.answer(f"{e.message}\nПопробуйте ещё.")
        return

    ach = AchievementService(session)
    new_ach: list[str] = []
    if await ach.unlock(user, "first_game"):
        new_ach.append("🎮 Первая игра")

    user.profile.cities_score += result.points

    tg_id = message.from_user.id if message.from_user else 0

    if result.game_ended:
        _cancel_timer(tg_id)
        user.profile.total_games += 1
        if result.won:
            user.profile.total_wins += 1
        if result.won and await ach.unlock(user, "first_win"):
            new_ach.append("🏆 Первая победа")
        await state.clear()
        suffix = f"\n\n🎖 {', '.join(new_ach)}" if new_ach else ""
        await message.answer(
            _("game.win", score=result.points) + suffix,
            reply_markup=after_game_kb(_),
        )
        return

    ach_line = f"\n\n🎖 {', '.join(new_ach)}" if new_ach else ""
    bot_city_name = result.bot_city.name if result.bot_city else "—"
    bot_country = (
        result.bot_city.country
        if result.bot_city and result.bot_city.country
        else "—"
    )
    seconds = await _arm_timer(
        message.bot, message.chat.id, tg_id, game_id, state, _
    )
    text_out = _(
        "game.accepted",
        city=result.city.name,
        bot_city=bot_city_name,
        bot_country=bot_country,
        letter=(result.next_letter or "").upper(),
    )
    if seconds > 0:
        text_out = f"{text_out}\n\n{_('game.timer', seconds=seconds)}"
    await message.answer(text_out + ach_line, reply_markup=game_kb(_))


@router.callback_query(F.data == CB_SURRENDER)
async def surrender(cb: CallbackQuery, state: FSMContext, session, _, external) -> None:
    if cb.from_user is not None:
        _cancel_timer(cb.from_user.id)

    data = await state.get_data()
    game_id = data.get("game_id")
    if not game_id:
        await cb.answer("Активной игры нет")
        return

    game = await session.get(Game, game_id)
    if game and game.status == GameStatus.ACTIVE.value:
        users = UserService(session)
        user = await users.get_or_create(cb.from_user.id, cb.from_user.username)  # type: ignore[union-attr]
        games = GameService(session, external)
        await games.surrender(game)
        user.profile.total_games += 1

    await state.clear()
    if cb.message:
        await cb.message.edit_text(
            _("game.surrender"), reply_markup=after_game_kb(_)
        )
    await cb.answer()
