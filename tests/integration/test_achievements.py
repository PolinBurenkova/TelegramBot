"""Интеграционные тесты достижений.

Покрывают сидирование справочника (``AchievementService.seed``), разблокировку
через БД и чистую функцию ``check_achievements``. Сеть не используется.
"""
from __future__ import annotations

import pytest

from app.constants import (
    ACHIEVEMENT_FIRST_CITY,
    ACHIEVEMENT_GEO_MASTER,
    ACHIEVEMENT_LEGEND,
    ACHIEVEMENT_POLYGLOT,
    ACHIEVEMENT_TRAVELER,
    ACHIEVEMENT_WEATHER_WIZARD,
    ACHIEVEMENTS,
)
from app.services.achievement_checker import check_achievements
from app.services.achievement_service import AchievementService

pytestmark = pytest.mark.integration


async def test_seed_creates_all_achievements_from_constants(db_session):
    service = AchievementService(db_session)

    await service.seed()

    rows = await service.ach.list_all()
    by_code = {row.code: row for row in rows}
    assert len(rows) == len(ACHIEVEMENTS)
    assert set(by_code) == set(ACHIEVEMENTS)
    for code, meta in ACHIEVEMENTS.items():
        assert by_code[code].title == meta["title"]
        assert by_code[code].description == meta["desc"]
        assert by_code[code].icon == meta["title"][:2]


async def test_seed_is_idempotent(db_session):
    service = AchievementService(db_session)
    await service.seed()
    first_ids = {row.code: row.id for row in await service.ach.list_all()}

    await service.seed()

    second_ids = {row.code: row.id for row in await service.ach.list_all()}
    assert second_ids == first_ids


async def test_unlock_unknown_code_returns_false(db_session, sample_user):
    service = AchievementService(db_session)
    await service.seed()

    assert await service.unlock(sample_user, "no_such_code") is False
    assert await service.user_ach.count_by_user(sample_user.id) == 0


async def test_unlock_known_code_is_idempotent(db_session, sample_user):
    service = AchievementService(db_session)
    await service.seed()

    assert await service.unlock(sample_user, ACHIEVEMENT_FIRST_CITY) is True
    assert await service.unlock(sample_user, ACHIEVEMENT_FIRST_CITY) is False
    assert await service.user_ach.count_by_user(sample_user.id) == 1


async def test_list_for_user_marks_unlocked_flags(db_session, sample_user):
    service = AchievementService(db_session)
    await service.seed()
    await service.unlock(sample_user, ACHIEVEMENT_TRAVELER)

    listed = await service.list_for_user(sample_user)

    assert len(listed) == len(ACHIEVEMENTS)
    flags = {ach.code: unlocked for ach, unlocked in listed}
    assert flags[ACHIEVEMENT_TRAVELER] is True
    assert flags[ACHIEVEMENT_FIRST_CITY] is False


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param(
            {"cities_used": 0, "countries_visited": 0, "xp": 0, "geo_avg_score": 0.0},
            [],
            id="nothing",
        ),
        pytest.param(
            {"cities_used": 1, "countries_visited": 0, "xp": 0, "geo_avg_score": 0.0},
            [ACHIEVEMENT_FIRST_CITY],
            id="first-city",
        ),
        pytest.param(
            {"cities_used": 49, "countries_visited": 0, "xp": 0, "geo_avg_score": 0.0},
            [ACHIEVEMENT_FIRST_CITY],
            id="almost-polyglot",
        ),
        pytest.param(
            {"cities_used": 50, "countries_visited": 0, "xp": 0, "geo_avg_score": 0.0},
            [ACHIEVEMENT_FIRST_CITY, ACHIEVEMENT_POLYGLOT],
            id="polyglot",
        ),
        pytest.param(
            {"cities_used": 0, "countries_visited": 10, "xp": 0, "geo_avg_score": 0.0},
            [ACHIEVEMENT_TRAVELER],
            id="traveler",
        ),
        pytest.param(
            {"cities_used": 0, "countries_visited": 0, "xp": 1000, "geo_avg_score": 0.0},
            [ACHIEVEMENT_LEGEND],
            id="legend",
        ),
        pytest.param(
            {"cities_used": 0, "countries_visited": 0, "xp": 0, "geo_avg_score": 3000.0},
            [ACHIEVEMENT_GEO_MASTER],
            id="geo-master",
        ),
        pytest.param(
            {"cities_used": 0, "countries_visited": 0, "xp": 0, "geo_avg_score": 2999.9},
            [],
            id="geo-below-threshold",
        ),
        pytest.param(
            {
                "cities_used": 0,
                "countries_visited": 0,
                "xp": 0,
                "geo_avg_score": 0.0,
                "weather_requests": 20,
            },
            [ACHIEVEMENT_WEATHER_WIZARD],
            id="weather-wizard",
        ),
        pytest.param(
            {
                "cities_used": 0,
                "countries_visited": 0,
                "xp": 0,
                "geo_avg_score": 0.0,
                "weather_requests": 19,
            },
            [],
            id="weather-below-threshold",
        ),
    ],
)
def test_check_achievements_thresholds(kwargs, expected):
    assert check_achievements(**kwargs) == expected


def test_check_achievements_returns_fixed_order_for_all():
    unlocked = check_achievements(
        cities_used=50,
        countries_visited=10,
        xp=1000,
        geo_avg_score=3000.0,
        weather_requests=20,
    )

    assert unlocked == [
        ACHIEVEMENT_FIRST_CITY,
        ACHIEVEMENT_POLYGLOT,
        ACHIEVEMENT_TRAVELER,
        ACHIEVEMENT_LEGEND,
        ACHIEVEMENT_GEO_MASTER,
        ACHIEVEMENT_WEATHER_WIZARD,
    ]


def test_check_achievements_never_returns_game_and_win_codes():
    unlocked = check_achievements(
        cities_used=1000,
        countries_visited=1000,
        xp=100_000,
        geo_avg_score=5000.0,
        weather_requests=1000,
    )

    assert "first_game" not in unlocked
    assert "first_win" not in unlocked
