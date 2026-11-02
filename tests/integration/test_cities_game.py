"""Интеграционные тесты игрового цикла «Города».

Сценарии строятся на реальных сервисах и репозиториях поверх сессии из
``db_session``. Все города заранее засеяны в БД, поэтому внешние геокодеры
не вызываются. Ограничение по населению снято, стартовый город выбирается
случайно, поэтому тесты ходов фиксируют его фикстурой ``fixed_starter``.
"""
from __future__ import annotations

import pytest

from app.constants import WIN_BONUS
from app.exceptions import (
    CityAlreadyUsed,
    CityNotFound,
    GameNotFound,
    WrongLetter,
)
from app.models.enums import GameStatus
from app.repositories.city_repo import CityRepo
from app.repositories.game_repo import GameRepo
from app.services.city_service import CityService
from app.services.game_service import GameService
from app.utils.validators import normalize_city

pytestmark = pytest.mark.integration

MOSCOW = "Москва"
ARZAMAS = "Арзамас"
SOCHI = "Сочи"
ABAKAN = "Абакан"


def _status(game) -> str:
    return getattr(game.status, "value", game.status)


async def _seed_city(db_session, name: str, *, population: int) -> None:
    await CityRepo(db_session).create(
        name=name,
        normalized_name=normalize_city(name),
        country_code="RU",
        country_name="Россия",
        region=None,
        population=population,
        lat=55.0,
        lon=37.0,
        source="test",
    )


async def _seed_moscow(db_session) -> None:
    await _seed_city(db_session, MOSCOW, population=13_000_000)


async def _seed_playable_cities(db_session) -> None:
    await _seed_moscow(db_session)
    await _seed_city(db_session, ARZAMAS, population=100_000)
    await _seed_city(db_session, SOCHI, population=425_000)


@pytest.fixture
def fixed_starter(monkeypatch):
    """Зафиксировать стартовый город по имени.

    Порог по населению снят, и ``start_game`` берёт случайный город; тесты
    ходов проверяют саму механику, поэтому выбирают стартер явно.
    """

    def _fix(name: str) -> None:
        async def _random(self, min_population=None):
            return await self.repo.get_by_name(name)

        monkeypatch.setattr(CityService, "random", _random)

    return _fix


async def test_start_game_creates_active_game_with_bot_starter(db_session, sample_user):
    await _seed_moscow(db_session)
    service = GameService(db_session)

    game = await service.start_game(sample_user)

    assert game is not None
    assert _status(game) == GameStatus.ACTIVE.value
    assert getattr(game.game_type, "value", game.game_type) == "cities"
    assert game.user_id == sample_user.id
    assert game.difficulty == "easy"
    assert game.meta == {"start_letter": "м"}
    assert game.score == 0
    assert game.moves_count == 1
    moves = await service.moves.list_by_game(game.id)
    assert len(moves) == 1
    assert moves[0].city_name == MOSCOW
    assert moves[0].is_user is False
    assert moves[0].move_number == 1
    assert moves[0].points == 0
    assert await service.used.list_by_game(game.id) == [normalize_city(MOSCOW)]
    assert await service.get_active(sample_user) is not None


async def test_start_game_finishes_previous_active_game(db_session, sample_user):
    await _seed_moscow(db_session)
    service = GameService(db_session)
    first = await service.start_game(sample_user)

    second = await service.start_game(sample_user)

    assert second is not None
    assert second.id != first.id
    assert _status(first) == GameStatus.FINISHED.value
    assert first.won is False
    assert _status(second) == GameStatus.ACTIVE.value
    assert await service.games.count_by_user(sample_user.id) == 2
    assert (await service.get_active(sample_user)).id == second.id


async def test_start_game_returns_none_without_cities(db_session, sample_user):
    service = GameService(db_session)

    assert await service.start_game(sample_user) is None
    assert await service.games.count_by_user(sample_user.id) == 0


async def test_start_game_allows_small_city_without_population_limit(
    db_session, sample_user
):
    """Ограничение по населению снято: город на 400 000 может быть стартером."""
    await _seed_city(db_session, "Тверь", population=400_000)
    service = GameService(db_session)

    game = await service.start_game(sample_user)

    assert game is not None
    assert game.meta == {"start_letter": "т"}
    moves = await service.moves.list_by_game(game.id)
    assert moves[0].city_name == "Тверь"


async def test_start_game_uses_requested_difficulty(db_session, sample_user):
    await _seed_moscow(db_session)
    service = GameService(db_session)

    game = await service.start_game(sample_user, difficulty="hard")

    assert game is not None
    assert game.difficulty == "hard"


async def test_make_move_normal_path(db_session, sample_user, fixed_starter):
    await _seed_playable_cities(db_session)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)

    result = await service.make_move(game, sample_user, ARZAMAS)

    assert result.city.name == ARZAMAS
    assert result.city.country_code == "RU"
    assert result.points == 13
    assert result.bot_city is not None
    assert result.bot_city.name == SOCHI
    assert result.game_ended is False
    assert result.won is False
    assert result.next_letter == "и"
    assert game.score == 13
    assert game.moves_count == 3
    assert _status(game) == GameStatus.ACTIVE.value
    used = await service.used.list_by_game(game.id)
    assert sorted(used) == sorted(
        [normalize_city(MOSCOW), normalize_city(ARZAMAS), normalize_city(SOCHI)]
    )
    moves = await service.moves.list_by_game(game.id)
    assert [move.city_name for move in moves] == [MOSCOW, ARZAMAS, SOCHI]
    assert [move.is_user for move in moves] == [False, True, False]
    assert moves[1].points == 13


async def test_make_move_win_path(db_session, sample_user, fixed_starter):
    await _seed_moscow(db_session)
    await _seed_city(db_session, ABAKAN, population=180_000)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)

    result = await service.make_move(game, sample_user, ABAKAN)

    assert result.city.name == ABAKAN
    assert result.points == 12
    assert result.bot_city is None
    assert result.game_ended is True
    assert result.won is True
    assert result.next_letter is None
    assert game.score == 12 + WIN_BONUS
    assert game.won is True
    assert _status(game) == GameStatus.FINISHED.value
    assert await service.get_active(sample_user) is None


async def test_make_move_rejects_repeated_city(db_session, sample_user, fixed_starter):
    await _seed_playable_cities(db_session)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)
    await service.make_move(game, sample_user, ARZAMAS)

    with pytest.raises(CityAlreadyUsed):
        await service.make_move(game, sample_user, ARZAMAS)


async def test_make_move_requires_expected_letter(
    db_session, sample_user, fixed_starter
):
    await _seed_playable_cities(db_session)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)

    with pytest.raises(WrongLetter) as excinfo:
        await service.make_move(game, sample_user, "Тверь")

    assert "А" in str(excinfo.value)


async def test_make_move_without_previous_move_raises_game_not_found(
    db_session, sample_user
):
    await _seed_playable_cities(db_session)
    game = await GameRepo(db_session).create_active(user_id=sample_user.id)
    service = GameService(db_session)

    with pytest.raises(GameNotFound) as excinfo:
        await service.make_move(game, sample_user, ARZAMAS)

    assert "Нет предыдущего хода" in str(excinfo.value)


async def test_make_move_unknown_city_raises_city_not_found(
    db_session, sample_user, monkeypatch, fixed_starter
):
    await _seed_playable_cities(db_session)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)

    async def _no_external(self, name: str):
        return None

    monkeypatch.setattr(CityService, "_fetch_external", _no_external)

    with pytest.raises(CityNotFound):
        await service.make_move(game, sample_user, "Анапа")


async def test_surrender_finishes_game_and_returns_score(
    db_session, sample_user, fixed_starter
):
    await _seed_playable_cities(db_session)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)
    await service.make_move(game, sample_user, ARZAMAS)

    score = await service.surrender(game)

    assert score == 13
    assert _status(game) == GameStatus.FINISHED.value
    assert game.won is False
    assert await service.get_active(sample_user) is None


async def test_timeout_finishes_game_with_timeout_status(
    db_session, sample_user, fixed_starter
):
    """Истёкшее время на ход завершает партию статусом ``timeout``."""
    await _seed_moscow(db_session)
    fixed_starter(MOSCOW)
    service = GameService(db_session)
    game = await service.start_game(sample_user)

    score = await service.timeout(game)

    assert score == 0
    assert _status(game) == GameStatus.TIMEOUT.value
    assert game.won is False
    assert game.finished_at is not None
    assert await service.get_active(sample_user) is None


async def test_bot_answers_on_k_letter_after_nalchik(
    db_session, sample_user, fixed_starter
):
    """Регресс: стартер на «н» (как в healthcheck).

    Раньше набор сидов покрывал только ветку «а», и при стартере «Астрахань»
    бот не находил город на «к», сдавался и отдавал победу пользователю.
    Стартер фиксируется явно: порог по населению снят, выбор случаен.
    """
    await _seed_city(db_session, "Астрахань", population=525_000)
    await _seed_city(db_session, "Нальчик", population=240_000)
    await _seed_city(db_session, "Курск", population=450_000)
    fixed_starter("Астрахань")
    service = GameService(db_session)

    game = await service.start_game(sample_user)
    assert game is not None

    result = await service.make_move(game, sample_user, "Нальчик")

    assert result.bot_city is not None
    assert result.bot_city.name == "Курск"
    assert result.next_letter == "к"
    assert result.game_ended is False
    assert game.moves_count == 3
