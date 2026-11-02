"""Интеграционные тесты профиля игрока.

Профиль создаётся вместе с пользователем (``UserRepo.create_with_profile``),
очки/уровень меняются через ``ProfileRepo``. Отдельного ``ProfileService``
в проекте нет, поэтому проверяется связка репозиториев и моделей.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.profile_repo import ProfileRepo
from app.repositories.user_repo import UserRepo

pytestmark = pytest.mark.integration


async def test_create_with_profile_creates_linked_profile_with_defaults(db_session):
    user = await UserRepo(db_session).create_with_profile(4_242, "profile_user")

    assert user.id is not None
    assert user.profile is not None
    assert user.profile.user_id == user.id
    assert user.profile.games_played == 0
    assert user.profile.games_won == 0
    assert user.profile.cities_named == 0
    assert user.profile.xp == 0
    assert user.profile.level == 1
    assert user.profile.cities_score == 0
    assert user.profile.geo_score == 0
    assert user.profile.streak_days == 0
    assert user.profile.last_played_at is None


async def test_get_by_tg_id_eager_loads_profile(db_session):
    user = await UserRepo(db_session).create_with_profile(4_243, "eager")
    repo = UserRepo(db_session)

    loaded = await repo.get_by_tg_id(4_243)

    assert loaded is not None
    assert loaded.profile is not None
    assert loaded.profile.id == user.profile.id


async def test_get_by_user_and_missing_profile(db_session):
    repo = ProfileRepo(db_session)
    user = await UserRepo(db_session).create_with_profile(4_244, "prof")

    found = await repo.get_by_user(user.id)

    assert found is not None
    assert found.user_id == user.id
    assert await repo.get_by_user(9_999_999) is None


async def test_add_xp_accumulates(db_session):
    repo = ProfileRepo(db_session)
    user = await UserRepo(db_session).create_with_profile(4_245, "xp")
    profile = await repo.get_by_user(user.id)

    await repo.add_xp(profile, 25)
    await repo.add_xp(profile, 17)

    assert profile.xp == 42


@pytest.mark.parametrize(
    ("field", "value", "attr"),
    [
        ("games_played", 3, "games_played"),
        ("games_won", 2, "games_won"),
        ("cities_named", 11, "cities_named"),
        ("cities_score", 30, "cities_score"),
        ("geo_score", 15, "geo_score"),
        ("streak_days", 4, "streak_days"),
    ],
)
async def test_increment_accumulates_field(db_session, field, value, attr):
    repo = ProfileRepo(db_session)
    user = await UserRepo(db_session).create_with_profile(4_246, "inc")
    profile = await repo.get_by_user(user.id)

    await repo.increment(profile, field, value)
    await repo.increment(profile, field, value)

    assert getattr(profile, attr) == value * 2


async def test_reset_clears_progress_and_keeps_level_one(db_session):
    repo = ProfileRepo(db_session)
    user = await UserRepo(db_session).create_with_profile(4_247, "reset")
    profile = await repo.get_by_user(user.id)
    profile.games_played = 10
    profile.games_won = 7
    profile.xp = 500
    profile.level = 9
    profile.cities_score = 120
    profile.geo_score = 80
    profile.streak_days = 5
    profile.last_played_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await db_session.flush()

    await repo.reset(profile)

    assert profile.games_played == 0
    assert profile.games_won == 0
    assert profile.xp == 0
    assert profile.level == 1
    assert profile.cities_score == 0
    assert profile.geo_score == 0
    assert profile.streak_days == 0
    assert profile.last_played_at is None


async def test_total_games_and_total_wins_properties_reflect_counters(db_session):
    user = await UserRepo(db_session).create_with_profile(4_248, "props")
    profile = await ProfileRepo(db_session).get_by_user(user.id)

    profile.total_games = 6
    profile.total_wins = 4

    assert profile.games_played == 6
    assert profile.games_won == 4
    assert profile.total_games == 6
    assert profile.total_wins == 4


async def test_create_with_profile_rejects_duplicate_tg_id(db_session):
    repo = UserRepo(db_session)
    await repo.create_with_profile(4_249, "first")

    with pytest.raises(IntegrityError):
        await repo.create_with_profile(4_249, "second")
