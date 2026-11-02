"""GeoGuessr — хендлеры."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.fsm.geo_states import GeoGame
from app.keyboards.geoguessr import geo_kb
from app.services.geo_game_service import GeoGameService
from app.services.geo_location_service import GeoLocationService
from app.services.map_renderer import build_static_map_url
from app.services.panorama_service import PanoramaService
from app.utils.validators import is_valid_city_name

router = Router(name="geoguessr")


@router.message(Command("geo"))
async def cmd_geo(message: Message, state: FSMContext, session, user) -> None:
    await state.clear()
    loc_service = GeoLocationService(session)
    loc = await loc_service.random(difficulty=user.difficulty or "medium")
    if loc is None:
        await message.answer("😔 Нет доступных локаций. Попробуйте позже.")
        return

    panorama_service = PanoramaService()
    pano = await panorama_service.get_panorama(loc.lat, loc.lon)

    geo_game = GeoGameService(session)
    game = await geo_game.start(user.id)

    await state.set_state(GeoGame.waiting_answer)
    await state.update_data(
        game_id=game.id,
        real_lat=loc.lat,
        real_lon=loc.lon,
        real_country=loc.country_code,
    )

    pano_url = (pano or {}).get("image_url")
    text = (
        "🌍 <b>GeoGuessr</b>\n\n"
        "Посмотри панораму и угадай, где это.\n"
        "Напиши название города или отправь геолокацию."
    )
    await message.answer(text, reply_markup=geo_kb(pano_url))
    if pano_url:
        try:
            await message.answer_photo(pano_url)
        except Exception:
            pass


@router.message(GeoGame.waiting_answer, F.location)
async def on_location(message: Message, state: FSMContext, session) -> None:
    await _handle_answer(
        message,
        state,
        session,
        message.location.latitude,
        message.location.longitude,
    )


@router.message(GeoGame.waiting_answer, F.text)
async def on_text_answer(message: Message, state: FSMContext, session) -> None:
    text = (message.text or "").strip()
    if not is_valid_city_name(text):
        await message.answer("🤔 Введите название города.")
        return

    from app.services.city_service import CityService

    try:
        city = await CityService(session).get_or_raise(text)
    except Exception:
        await message.answer("🤔 Не нашёл такой город. Попробуйте ещё.")
        return

    await _handle_answer(message, state, session, city["lat"], city["lon"])


async def _handle_answer(
    message: Message, state: FSMContext, session, guess_lat: float, guess_lon: float
) -> None:
    data = await state.get_data()
    from app.models.game import Game

    game = await session.get(Game, data["game_id"])
    if game is None:
        await state.clear()
        await message.answer("Игра не найдена.")
        return

    service = GeoGameService(session)
    result = await service.check_answer(
        game=game,
        real_lat=data["real_lat"],
        real_lon=data["real_lon"],
        guess_lat=guess_lat,
        guess_lon=guess_lon,
    )

    map_url = build_static_map_url(
        data["real_lat"], data["real_lon"], guess_lat, guess_lon
    )
    text = (
        f"📍 Расстояние: <b>{result['distance_km']:.1f} км</b>\n"
        f"🏆 Очки: <b>{result['score']}</b> из 5000\n"
        f"Всего за игру: {game.score}"
    )
    await message.answer(text, reply_markup=geo_kb(map_url))
    await state.set_state(GeoGame.showing_result)


@router.callback_query(F.data == "geo:skip")
async def on_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Пропущено.")
    await callback.answer()