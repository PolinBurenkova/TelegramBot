"""Интеграционные тесты лидерборда.

``LeaderboardService`` собирает топ по сумме игровых очков
(``Profile.cities_score + Profile.geo_score``) через ``StatsRepo.top_users``.
Проверяется порядок, ранги, форма записи, лимит и отбор только пользователей
с профилем.
"""
from __future__ import annotations

import pytest

from app.repositories.profile_repo import ProfileRepo
from app.repositories.user_repo import UserRepo
from app.services.leaderboard_service import LeaderboardService

pytestmark = pytest.mark.integration


async def _set_scores(db_session, *, user, cities: int = 0, geo: int = 0) -> None:
    profile = await ProfileRepo(db_session).get_by_user(user.id)
    assert profile is not None
    profile.cities_score = cities
    profile.geo_score = geo
    await db_session.flush()


async def test_top_orders_by_combined_score_and_ranks(db_session):
    users = UserRepo(db_session)
    top_user = await users.create_with_profile(555, "top")
    middle_user = await users.create_with_profile(111, "middle")
    last_user = await users.create_with_profile(222, "last")
    await _set_scores(db_session, user=top_user, cities=50, geo=50)
    await _set_scores(db_session, user=middle_user, cities=60, geo=0)
    await _set_scores(db_session, user=last_user, cities=0, geo=10)
    service = LeaderboardService(db_session)

    rows = await service.top()

    assert [row["telegram_id"] for row in rows] == [555, 111, 222]
    assert [row["rank"] for row in rows] == [1, 2, 3]


async def test_top_entry_shape_and_username_fallback(db_session):
    user = await UserRepo(db_session).create_with_profile(777, None)
    service = LeaderboardService(db_session)

    rows = await service.top()

    assert len(rows) == 1
    entry = rows[0]
    assert set(entry) == {"rank", "first_name", "username", "telegram_id", "xp", "level"}
    assert entry["first_name"] is None
    assert entry["username"] == "user_777"
    assert entry["telegram_id"] == 777
    assert entry["xp"] == 0
    assert entry["level"] == 1
    assert entry["rank"] == 1


async def test_top_uses_xp_and_level_from_profile(db_session):
    user = await UserRepo(db_session).create_with_profile(888, "hero")
    profile = await ProfileRepo(db_session).get_by_user(user.id)
    profile.xp = 420
    profile.level = 7
    await db_session.flush()
    service = LeaderboardService(db_session)

    entry = (await service.top())[0]

    assert entry["xp"] == 420
    assert entry["level"] == 7


async def test_top_respects_limit(db_session):
    users = UserRepo(db_session)
    for tg_id in (1, 2, 3):
        await users.create_with_profile(tg_id, f"u{tg_id}")
    service = LeaderboardService(db_session)

    rows = await service.top(limit=2)

    assert len(rows) == 2
    assert [row["rank"] for row in rows] == [1, 2]


async def test_top_returns_empty_list_for_empty_db(db_session):
    assert await LeaderboardService(db_session).top() == []


async def test_top_excludes_users_without_profile(db_session):
    users = UserRepo(db_session)
    await users.create_with_profile(1_001, "with_profile")
    await users.create(tg_id=1_002, username="no_profile")
    service = LeaderboardService(db_session)

    rows = await service.top()

    assert [row["telegram_id"] for row in rows] == [1_001]
