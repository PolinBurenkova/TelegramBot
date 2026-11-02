"""Интеграционные тесты GeoGuessr-цикла.

``GeoGameService`` создаёт игру и считает очки/XP за ответ без сети:
координаты передаются явно, расстояние считается по haversine.
"""
from __future__ import annotations

import pytest

from app.constants import GEO_MAX_SCORE, XP_FOR_GEO
from app.models.enums import GameStatus, GameType
from app.repositories.profile_repo import ProfileRepo
from app.repositories.user_repo import UserRepo
from app.services.geo_game_service import GeoGameService
from app.services.geo_score import calculate_score, haversine

pytestmark = pytest.mark.integration

MOSCOW = (55.7558, 37.6173)


def _status(game) -> str:
    return getattr(game.status, "value", game.status)


async def test_start_creates_active_geoguessr_game(db_session, sample_user):
    service = GeoGameService(db_session)

    game = await service.start(sample_user.id)

    assert game.id is not None
    assert game.user_id == sample_user.id
    assert getattr(game.game_type, "value", game.game_type) == GameType.GEOGUESSR.value
    assert _status(game) == GameStatus.ACTIVE.value
    assert game.started_at is not None


async def test_check_answer_exact_guess_awards_max_score_and_xp(db_session, sample_user):
    service = GeoGameService(db_session)
    game = await service.start(sample_user.id)

    result = await service.check_answer(
        game, MOSCOW[0], MOSCOW[1], MOSCOW[0], MOSCOW[1]
    )

    assert result["distance_km"] == pytest.approx(0.0)
    assert result["score"] == GEO_MAX_SCORE
    profile = await ProfileRepo(db_session).get_by_user(sample_user.id)
    assert profile.xp == XP_FOR_GEO
    assert game.score == GEO_MAX_SCORE


async def test_check_answer_decays_score_with_distance(db_session, sample_user):
    service = GeoGameService(db_session)
    game = await service.start(sample_user.id)
    guess = (48.8566, 2.3522)

    result = await service.check_answer(
        game, MOSCOW[0], MOSCOW[1], guess[0], guess[1]
    )

    expected_distance = haversine(MOSCOW[0], MOSCOW[1], guess[0], guess[1])
    expected_score = calculate_score(expected_distance)
    assert result["distance_km"] == pytest.approx(expected_distance)
    assert result["score"] == expected_score
    assert 0 < result["score"] < GEO_MAX_SCORE


@pytest.mark.parametrize(
    "guess",
    [
        pytest.param(MOSCOW, id="exact"),
        pytest.param((59.9343, 30.3351), id="saint-petersburg"),
    ],
)
async def test_check_answer_accumulates_score_and_xp(db_session, sample_user, guess):
    service = GeoGameService(db_session)
    game = await service.start(sample_user.id)
    profile = await ProfileRepo(db_session).get_by_user(sample_user.id)

    first = await service.check_answer(
        game, MOSCOW[0], MOSCOW[1], MOSCOW[0], MOSCOW[1]
    )
    second = await service.check_answer(game, MOSCOW[0], MOSCOW[1], guess[0], guess[1])

    assert game.score == first["score"] + second["score"]
    assert profile.xp == XP_FOR_GEO * 2


async def test_check_answer_works_without_profile(db_session):
    user = await UserRepo(db_session).create(tg_id=1_234_567, username="noprofile")
    await db_session.flush()
    service = GeoGameService(db_session)
    game = await service.start(user.id)

    result = await service.check_answer(
        game, MOSCOW[0], MOSCOW[1], MOSCOW[0], MOSCOW[1]
    )

    assert result["score"] == GEO_MAX_SCORE
    assert await ProfileRepo(db_session).get_by_user(user.id) is None
