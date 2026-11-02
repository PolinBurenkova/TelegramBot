"""Интеграционные тесты репозиториев.

Проверяют реальные запросы SQLAlchemy 2.0 к БД из фикстуры ``db_session``
(SQLite in-memory, схема создаётся ``create_all`` на каждый тест).
Сеть и Redis не используются. Репозитории делают только ``flush()``,
поэтому проверки выполняются в рамках той же сессии.
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.city import City
from app.models.enums import GameStatus, GameType
from app.repositories.achievement_repo import AchievementRepo, UserAchievementRepo
from app.repositories.base import BaseRepo
from app.repositories.city_repo import CityRepo
from app.repositories.game_repo import GameRepo, MoveRepo
from app.repositories.geo_location_repo import GeoLocationRepo
from app.repositories.profile_repo import ProfileRepo
from app.repositories.stats_repo import StatsRepo
from app.repositories.user_repo import UserRepo
from app.repositories.user_used_city_repo import UserUsedCityRepo
from app.utils.validators import normalize_city

pytestmark = pytest.mark.integration


class _CityRepo(BaseRepo[City]):
    """Минимальный наследник BaseRepo для проверки общего CRUD."""

    model = City


def _status(game) -> str:
    """Значение Enum-колонки (на загрузке может быть и член, и строка)."""
    return getattr(game.status, "value", game.status)


def _city_row(name: str, *, population: int = 1_000, country_code: str = "RU") -> dict:
    return {
        "name": name,
        "normalized_name": normalize_city(name),
        "country_code": country_code,
        "country_name": "Россия",
        "population": population,
        "lat": 55.0,
        "lon": 37.0,
        "source": "test",
    }


def _geo_row(lat: float, lon: float, difficulty: str = "easy", source: str = "test") -> dict:
    return {
        "image_url": f"https://example.test/{lat}_{lon}.jpg",
        "lat": lat,
        "lon": lon,
        "difficulty": difficulty,
        "source": source,
    }


# --- BaseRepo ---------------------------------------------------------------


async def test_base_repo_create_assigns_id_and_get_returns_row(db_session):
    repo = _CityRepo(db_session)

    created = await repo.create(**_city_row("Тверь"))

    assert created.id is not None
    found = await repo.get(created.id)
    assert found is created
    assert found.name == "Тверь"


async def test_base_repo_get_missing_returns_none(db_session):
    repo = _CityRepo(db_session)

    assert await repo.get(10_000) is None


async def test_base_repo_list_supports_limit_and_offset(db_session):
    repo = _CityRepo(db_session)
    for name in ("Тверь", "Тула", "Томск"):
        await repo.create(**_city_row(name))

    page_one = await repo.list(limit=2)
    page_two = await repo.list(limit=2, offset=2)

    assert len(page_one) == 2
    assert len(page_two) == 1
    assert len(await repo.list()) == 3


async def test_base_repo_update_and_delete(db_session):
    repo = _CityRepo(db_session)
    city = await repo.create(**_city_row("Тверь"))

    await repo.update(city, population=42)
    assert city.population == 42

    await repo.delete(city)
    assert await repo.get(city.id) is None


async def test_base_repo_count(db_session):
    repo = _CityRepo(db_session)

    assert await repo.count() == 0
    await repo.create(**_city_row("Тверь"))
    await repo.create(**_city_row("Тула"))

    assert await repo.count() == 2


# --- GameRepo ---------------------------------------------------------------


async def test_game_repo_create_active_is_active_and_discoverable(db_session, sample_user):
    games = GameRepo(db_session)

    game = await games.create_active(user_id=sample_user.id)

    assert _status(game) == GameStatus.ACTIVE.value
    assert game.game_type == GameType.CITIES.value
    active = await games.get_active(sample_user.id)
    assert active is not None
    assert active.id == game.id


async def test_game_repo_get_active_filters_by_game_type(db_session, sample_user):
    games = GameRepo(db_session)
    await games.create_active(user_id=sample_user.id)

    assert await games.get_active(sample_user.id, game_type="geoguessr") is None


async def test_game_repo_finish_sets_status_won_score_and_timestamp(db_session, sample_user):
    games = GameRepo(db_session)
    game = await games.create_active(user_id=sample_user.id)

    await games.finish(game, won=True, score=42)

    assert _status(game) == GameStatus.FINISHED.value
    assert game.won is True
    assert game.score == 42
    assert game.finished_at is not None
    assert await games.get_active(sample_user.id) is None


async def test_game_repo_list_by_user_paginates_and_counts(db_session, sample_user):
    games = GameRepo(db_session)
    for _ in range(3):
        await games.create_active(user_id=sample_user.id)

    first = await games.list_by_user(sample_user.id, page=0, size=2)
    second = await games.list_by_user(sample_user.id, page=1, size=2)

    assert len(first) == 2
    assert len(second) == 1
    assert all(g.user_id == sample_user.id for g in first + second)
    assert await games.count_by_user(sample_user.id) == 3
    assert await games.count_by_user(sample_user.id + 1) == 0


# --- MoveRepo ---------------------------------------------------------------


async def test_move_repo_numbers_moves_and_normalizes_city(db_session, sample_user):
    games = GameRepo(db_session)
    moves = MoveRepo(db_session)
    game = await games.create_active(user_id=sample_user.id)

    first = await moves.create_move(game.id, "Москва", points=10)
    second = await moves.create_move(game.id, "Краснодар", is_user=False)
    third = await moves.create_move(game.id, "Рязань")

    assert first.move_number == 1
    assert first.normalized_name == "москва"
    assert first.is_user is True
    assert first.points == 10
    assert second.move_number == 2
    assert second.is_user is False
    assert third.move_number == 3
    assert await moves.next_move_number(game.id) == 4
    last = await moves.last_move(game.id)
    assert last is not None
    assert last.city_name == "Рязань"


async def test_move_repo_last_move_none_for_empty_game(db_session, sample_user):
    games = GameRepo(db_session)
    moves = MoveRepo(db_session)
    game = await games.create_active(user_id=sample_user.id)

    assert await moves.last_move(game.id) is None
    assert await moves.next_move_number(game.id) == 1


async def test_move_repo_rejects_duplicate_city_in_same_game(db_session, sample_user):
    games = GameRepo(db_session)
    moves = MoveRepo(db_session)
    game = await games.create_active(user_id=sample_user.id)
    await moves.create_move(game.id, "Москва")

    with pytest.raises(IntegrityError):
        await moves.create_move(game.id, "  москва  ")


async def test_move_repo_list_by_game_ordered_by_move_number(db_session, sample_user):
    games = GameRepo(db_session)
    moves = MoveRepo(db_session)
    game = await games.create_active(user_id=sample_user.id)
    for name in ("Москва", "Краснодар", "Рязань"):
        await moves.create_move(game.id, name)

    listed = await moves.list_by_game(game.id)

    assert [m.move_number for m in listed] == [1, 2, 3]
    assert [m.city_name for m in listed] == ["Москва", "Краснодар", "Рязань"]


# --- CityRepo ---------------------------------------------------------------


async def test_city_repo_get_by_name_normalizes_input(db_session, sample_city):
    repo = CityRepo(db_session)

    found = await repo.get_by_name("  МОСКВА ")
    missing = await repo.get_by_name("Атлантида")

    assert found is not None
    assert found.id == sample_city.id
    assert missing is None


async def test_city_repo_search_orders_by_population_desc(db_session):
    repo = CityRepo(db_session)
    await repo.create(**_city_row("Мурманск", population=270_000))
    await repo.create(**_city_row("Москва", population=13_000_000))
    await repo.create(**_city_row("Казань", population=1_200_000))

    found = await repo.search("М")

    assert [c.name for c in found] == ["Москва", "Мурманск"]


async def test_city_repo_list_starting_with_respects_limit(db_session):
    repo = CityRepo(db_session)
    await repo.create(**_city_row("Москва", population=13_000_000))
    await repo.create(**_city_row("Мурманск", population=270_000))
    await repo.create(**_city_row("Тверь", population=400_000))

    assert len(await repo.list_starting_with("м")) == 2
    assert len(await repo.list_starting_with("м", limit=1)) == 1
    assert await repo.list_starting_with("я") == []


async def test_city_repo_random_applies_population_filter(db_session):
    repo = CityRepo(db_session)
    await repo.create(**_city_row("Москва", population=13_000_000))
    await repo.create(**_city_row("Тверь", population=400_000))

    picked = await repo.random(min_population=500_000)

    assert picked is not None
    assert picked.name == "Москва"
    assert await repo.random(country_code="KZ") is None


async def test_city_repo_create_from_geonames_maps_and_sanitizes_fields(db_session):
    repo = CityRepo(db_session)

    city = await repo.create_from_geonames(
        {
            "name": "Казань",
            "country_code": "ru",
            "country_name": None,
            "population": "1200000",
            "lat": "55.79",
            "lng": "49.12",
            "source": "geonames",
        }
    )

    assert city.normalized_name == "казань"
    assert city.country_code == "RU"
    assert city.country_name == ""
    assert city.population == 1_200_000
    assert city.lat == pytest.approx(55.79)
    assert city.lon == pytest.approx(49.12)
    assert city.source == "geonames"


async def test_city_repo_create_from_geonames_uses_fallbacks(db_session):
    repo = CityRepo(db_session)

    city = await repo.create_from_geonames(
        {"name": "Уфа", "country_code": None, "population": None, "lat": None, "source": "s" * 25}
    )

    assert city.country_code == "XX"
    assert city.population == 0
    assert city.lat == 0.0
    assert city.lon == 0.0
    assert city.source == "s" * 20


async def test_city_repo_bulk_insert_skips_duplicates(db_session):
    repo = CityRepo(db_session)
    await repo.create(**_city_row("Москва", population=13_000_000))

    inserted = await repo.bulk_insert([_city_row("Москва"), _city_row("Тула")])

    assert inserted == 1
    assert await repo.count() == 2


# --- UserRepo ---------------------------------------------------------------


async def test_user_repo_create_with_profile_and_lookup_by_tg_id(db_session):
    repo = UserRepo(db_session)

    user = await repo.create_with_profile(777, "u777")

    assert user.id is not None
    assert user.profile is not None
    assert user.profile.games_played == 0
    assert user.profile.level == 1
    found = await repo.get_by_tg_id(777)
    assert found is not None
    assert found.id == user.id
    assert found.profile is not None
    assert await repo.get_by_tg_id(778) is None


async def test_user_repo_setters_update_fields(db_session, sample_user):
    repo = UserRepo(db_session)

    await repo.update_locale(sample_user, "en")
    await repo.update_last_seen(sample_user)
    await repo.set_notify(sample_user, False)
    await repo.set_banned(sample_user, True)

    assert sample_user.locale == "en"
    assert sample_user.last_seen_at is not None
    assert sample_user.notify is False
    assert sample_user.is_banned is True


async def test_user_repo_list_for_broadcast_skips_banned_and_counts_all(db_session):
    repo = UserRepo(db_session)
    first = await repo.create_with_profile(1_001, "a")
    second = await repo.create_with_profile(1_002, "b")
    banned = await repo.create_with_profile(1_003, "c")
    await repo.set_banned(banned, True)

    recipients = await repo.list_for_broadcast(0, 10)
    page_two = await repo.list_for_broadcast(1, 1)

    assert {u.tg_id for u in recipients} == {first.tg_id, second.tg_id}
    assert len(page_two) == 1
    assert await repo.count_all() == 3


# --- GeoLocationRepo --------------------------------------------------------


async def test_geo_location_repo_random_by_difficulty_and_exclusions(db_session):
    repo = GeoLocationRepo(db_session)
    easy_one = await repo.create(**_geo_row(55.1, 37.1, "easy"))
    easy_two = await repo.create(**_geo_row(55.2, 37.2, "easy"))
    hard = await repo.create(**_geo_row(55.3, 37.3, "hard"))

    picked = await repo.random_by_difficulty("easy")
    assert picked is not None
    assert picked.id in {easy_one.id, easy_two.id}

    excluded = await repo.random_by_difficulty("easy", exclude_ids=[easy_one.id, easy_two.id])
    assert excluded is None
    picked_hard = await repo.random_by_difficulty("hard")
    assert picked_hard is not None
    assert picked_hard.id == hard.id


async def test_geo_location_repo_bulk_insert_deduplicates_by_coords(db_session):
    repo = GeoLocationRepo(db_session)
    rows = [_geo_row(55.1, 37.1), _geo_row(55.1, 37.1)]

    assert await repo.bulk_insert(rows) == 1
    assert await repo.count() == 1
    assert await repo.bulk_insert([_geo_row(55.2, 37.2)]) == 1
    assert await repo.count() == 2


async def test_geo_location_repo_get_by_coords(db_session):
    repo = GeoLocationRepo(db_session)
    created = await repo.create(**_geo_row(55.1, 37.1))

    found = await repo.get_by_coords(55.1, 37.1, "test")

    assert found is not None
    assert found.id == created.id
    assert await repo.get_by_coords(55.1, 37.1, "other") is None


# --- UserUsedCityRepo -------------------------------------------------------


async def test_user_used_city_repo_scopes_by_game_and_clears(db_session, sample_user):
    games = GameRepo(db_session)
    repo = UserUsedCityRepo(db_session)
    game = await games.create_active(user_id=sample_user.id)

    await repo.add(sample_user.id, "москва", game.id)

    assert await repo.exists(sample_user.id, "москва", game.id) is True
    assert await repo.exists(sample_user.id, "москва") is True
    assert await repo.exists(sample_user.id, "казань", game.id) is False
    assert await repo.list_by_game(game.id) == ["москва"]
    assert await repo.list_by_user(sample_user.id) == ["москва"]

    await repo.add(sample_user.id, "казань")
    assert len(await repo.list_by_user(sample_user.id)) == 2
    assert await repo.list_by_game(game.id) == ["москва"]

    assert await repo.clear_for_user(sample_user.id) == 2
    assert await repo.exists(sample_user.id, "москва") is False


# --- StatsRepo --------------------------------------------------------------


async def test_stats_repo_top_users_orders_by_total_score(db_session):
    users = UserRepo(db_session)
    profiles = ProfileRepo(db_session)
    high = await users.create_with_profile(9_001, "high")
    low = await users.create_with_profile(9_002, "low")
    high_profile = await profiles.get_by_user(high.id)
    low_profile = await profiles.get_by_user(low.id)
    high_profile.cities_score = 100
    low_profile.cities_score = 10
    low_profile.geo_score = 5
    await db_session.flush()

    rows = await StatsRepo(db_session).top_users()

    assert [u.tg_id for u, _ in rows] == [9_001, 9_002]
    assert len(await StatsRepo(db_session).top_users(limit=1)) == 1


async def test_stats_repo_win_rate_counts_finished_games(db_session):
    user = await UserRepo(db_session).create_with_profile(9_100, "w")
    games = GameRepo(db_session)
    won_game = await games.create_active(user_id=user.id)
    await games.finish(won_game, won=True)
    lost_game = await games.create_active(user_id=user.id)
    await games.finish(lost_game, won=False)
    await games.create_active(user_id=user.id)
    stats = StatsRepo(db_session)

    assert await stats.win_rate(user.id) == pytest.approx(0.5)
    assert await stats.win_rate(9_999) == 0.0


# --- Achievements -----------------------------------------------------------


async def test_achievement_repo_bulk_upsert_creates_then_updates(db_session):
    repo = AchievementRepo(db_session)
    row = {"code": "a1", "title": "Первый", "description": "d1", "icon": "Пе"}

    assert await repo.bulk_upsert([row]) == 1
    assert await repo.bulk_upsert([{**row, "title": "Второй"}]) == 1

    all_rows = await repo.list_all()
    assert len(all_rows) == 1
    assert all_rows[0].title == "Второй"
    assert (await repo.get_by_code("a1")).description == "d1"


async def test_user_achievement_repo_unlock_is_idempotent(db_session, sample_user):
    ach_repo = AchievementRepo(db_session)
    repo = UserAchievementRepo(db_session)
    ach = await ach_repo.create(code="a1", title="Первый", description="d1", icon="Пе")

    assert await repo.unlock(sample_user.id, ach.id) is True
    assert await repo.unlock(sample_user.id, ach.id) is False
    assert await repo.exists(sample_user.id, ach.id) is True
    assert await repo.count_by_user(sample_user.id) == 1
    assert await repo.unlocked_ids(sample_user.id) == {ach.id}
    assert len(await repo.list_by_user(sample_user.id)) == 1


async def test_user_achievement_unique_constraint(db_session, sample_user):
    ach_repo = AchievementRepo(db_session)
    repo = UserAchievementRepo(db_session)
    ach = await ach_repo.create(code="a1", title="Первый", description="d1", icon="Пе")
    await repo.create(user_id=sample_user.id, achievement_id=ach.id)

    with pytest.raises(IntegrityError):
        await repo.create(user_id=sample_user.id, achievement_id=ach.id)
