"""Офлайн-самопроверка «Города+»: БД, кэш, сервисы, движок игры, роутеры.

Не требует Telegram, Redis и внешних API — всё работает на SQLite +
встроенном InMemoryRedis. Отчёт пишется в logs/healthcheck.json.

Запуск:
    python scripts/healthcheck.py
Код возврата 0 — все проверки прошли, 1 — есть падения.
"""
from __future__ import annotations

import asyncio
import json
import sys
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS: list[dict[str, object]] = []


def record(name: str, status: str, detail: str = "") -> None:
    """Зафиксировать результат проверки."""
    RESULTS.append({"check": name, "status": status, "detail": detail})
    icon = {"ok": "OK  ", "fail": "FAIL", "skip": "SKIP"}[status]
    print(f"[{icon}] {name}" + (f" — {detail}" if detail else ""))


async def run_step(name: str, fn: Callable[[], Awaitable[str]]) -> None:
    """Выполнить проверку и записать итог."""
    try:
        detail = await fn()
        record(name, "ok", detail or "")
    except Exception as exc:  # noqa: BLE001 — отчёт должен пережить любую ошибку
        record(name, "fail", f"{type(exc).__name__}: {exc}")
        traceback.print_exc()


# ─────────────────────────── проверки ───────────────────────────


async def check_config() -> str:
    from app.config import get_settings

    s = get_settings()
    url = s.database_url or ""
    if not url:
        raise RuntimeError("DATABASE_URL пуст")
    mode = "sqlite" if url.startswith("sqlite") else "postgres"
    redis_mode = "redis" if (s.redis_url or "").strip() else "in-memory"
    return f"db={mode}, redis={redis_mode}, env={s.environment}"


async def check_imports() -> str:
    import importlib

    modules = [
        "app.config",
        "app.database",
        "app.models",
        "app.repositories.game_repo",
        "app.repositories.city_repo",
        "app.services.game_service",
        "app.services.city_service",
        "app.services.user_service",
        "app.services.geo_game_service",
        "app.services.external.registry",
        "app.utils.circuit_breaker",
        "app.utils.quota_manager",
        "app.utils.provider_chain",
        "app.handlers.router",
        "app.bot.dispatcher",
    ]
    for name in modules:
        importlib.import_module(name)
    return f"{len(modules)} модулей"


async def check_database() -> str:
    from sqlalchemy import inspect as sa_inspect

    from app.database import async_engine, init_models
    from app.models import Base

    await init_models()
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(lambda c: sa_inspect(c).get_table_names())
    missing = set(Base.metadata.tables) - set(tables)
    if missing:
        raise RuntimeError(f"нет таблиц: {sorted(missing)}")
    return f"{len(tables)} таблиц"


async def check_cache() -> str:
    from app.utils.cache import get_cache, get_redis

    cache = get_cache()
    await cache.set("hc:key", {"a": 1}, ttl=30)
    value = await cache.get("hc:key")
    if value != {"a": 1}:
        raise TypeError(f"cache get → {value!r}")
    redis = get_redis()
    await redis.set("hc:ping", "1")
    if await redis.get("hc:ping") != "1":
        raise TypeError("redis get → без значения")
    return type(cache).__name__ + "/" + type(redis).__name__


async def check_score() -> str:
    from app.services.score_service import ScoreService
    from app.utils.geo import haversine_km

    points = ScoreService.city_points("Волгоград", "easy")
    geo = ScoreService.geo_points(100.0)
    dist = haversine_km(55.75, 37.61, 59.93, 30.33)
    if points <= 0 or geo <= 0:
        raise ValueError(f"очки не растут: city={points}, geo={geo}")
    if not 620 <= dist <= 660:
        raise ValueError(f"Москва-Петербург = {dist:.1f} км, ожидалось ~635")
    return f"city={points}, geo(100км)={geo}, msk-spb={dist:.0f}км"


async def check_users() -> str:
    from app.database import async_session_factory
    from app.services.user_service import UserService

    async with async_session_factory() as session:
        service = UserService(session)
        user = await service.get_or_create(1_000_000_001, "healthcheck")
        view = await service.get_profile_view(user)
        await session.commit()
    return f"user={user.id}, level={getattr(view, 'level', '?')}"


async def _pick_user_answer(
    service: Any, required: str, starter_norm: str
) -> str | None:
    """Город для хода пользователя, после которого бот точно сможет ответить.

    Порог по населению снят, поэтому стартовым городом может стать любой из
    сидов. Здесь перебираются кандидаты на букву ``required`` и берётся первый,
    у которого есть продолжение (город на последнюю букву кандидата).
    """
    from app.utils.validators import last_letter

    repo = service.city_service.repo
    candidates = [
        city
        for city in await repo.list_starting_with(required, limit=50)
        if city.name_norm != starter_norm
    ]
    for candidate in candidates:
        follow_letter = last_letter(candidate.name)
        follow = [
            city
            for city in await repo.list_starting_with(follow_letter, limit=5)
            if city.name_norm not in {starter_norm, candidate.name_norm}
        ]
        if follow:
            return candidate.name
    return None


async def _seed_cities() -> None:
    """Города для проверки движка «Городов».

    Ограничение по населению снято, поэтому стартовым городом может стать
    любой из засеянных. Набор образует замкнутый цикл букв, чтобы для каждого
    возможного стартера нашлись и ход пользователя, и ответ бота:

        Москва(а) → Астрахань(н) → Нальчик(к) → Курск(к) → Киров(в)
                  → Вологда(а) → Астрахань…

    Отдельная ветка для «й»: Волжский(в…й) → Йошкар-Ола(й…а) → Астрахань…
    (правило: если город заканчивается на «й», следующий начинается на «й»).
    """
    from app.database import async_session_factory
    from app.repositories.city_repo import CityRepo

    data = [
        ("Москва", "москва", 55.7558, 37.6173, 13_000_000, "RU"),
        ("Астрахань", "астрахань", 46.3497, 48.0408, 525_000, "RU"),
        ("Анапа", "анапа", 44.8908, 37.3199, 180_000, "RU"),
        ("Нальчик", "нальчик", 43.4981, 43.6189, 240_000, "RU"),
        ("Волжский", "волжский", 48.7861, 44.7797, 320_000, "RU"),
        ("Йошкар-Ола", "йошкар-ола", 56.6388, 47.8908, 280_000, "RU"),
        ("Курск", "курск", 51.7304, 36.1926, 450_000, "RU"),
        ("Киров", "киров", 58.6035, 49.6679, 470_000, "RU"),
        ("Вологда", "вологда", 59.2205, 39.8915, 300_000, "RU"),
    ]
    async with async_session_factory() as session:
        repo = CityRepo(session)
        for name, norm, lat, lon, pop, cc in data:
            existing = await repo.get_by_name(name)
            if existing:
                continue
            await repo.create(
                name=name,
                normalized_name=norm,
                lat=lat,
                lon=lon,
                population=pop,
                country_code=cc,
                country_name="Россия",
                source="seed",
            )
        await session.commit()


async def check_cities() -> str:
    from app.database import async_session_factory
    from app.services.city_service import CityService

    await _seed_cities()
    async with async_session_factory() as session:
        service = CityService(session)
        city = await service.find("Москва")
        if city is None:
            raise LookupError("город Москва не найден после сидирования")
        roubles = await service.repo.list_starting_with("а", limit=20)
    return f"найдено: {city.name}, на «а»: {len(roubles)}"


async def check_game_engine() -> str:
    from app.database import async_session_factory
    from app.exceptions import CityAlreadyUsed, WrongLetter
    from app.repositories.game_repo import GameRepo, MoveRepo
    from app.repositories.user_used_city_repo import UserUsedCityRepo
    from app.services.city_service import CityService
    from app.services.game_service import GameService
    from app.services.user_service import UserService
    from app.utils.validators import last_letter, normalize_city

    await _seed_cities()
    async with async_session_factory() as session:
        user = await UserService(session).get_or_create(1_000_000_002, "hc_game")
        games = GameRepo(session)
        moves = MoveRepo(session)
        used = UserUsedCityRepo(session)

        service = GameService(session, external=None)
        # Порог по населению снят, поэтому стартовый город выбирается случайно
        # из всей БД. Для проверки фиксируем его: иначе буква старта зависит от
        # содержимого рабочей базы и шаг становится недетерминированным.
        starter_city = await service.city_service.repo.get_by_name("Москва")
        if starter_city is None:
            raise LookupError("сид «Москва» не найден в справочнике")

        async def _fixed_starter(min_population: int | None = None):
            return starter_city

        service.city_service.random = _fixed_starter  # type: ignore[method-assign]
        stale = await games.get_active(user.id)
        while stale is not None:
            await games.finish(stale, won=False)
            stale = await games.get_active(user.id)
        await session.commit()

        game = await service.start_game(user)
        if game is None:
            raise LookupError("start_game не смог выбрать стартовый город")

        last = await moves.last_move(game.id)
        if last is None:
            raise LookupError("стартовый ход не записан")
        required = last_letter(last.city_name)

        wrong = "Волгоград" if required != "в" else "Анапа"
        try:
            await service.make_move(game, user, wrong)
        except WrongLetter:
            pass
        else:
            raise AssertionError("неверная буква не отвергнута")

        try:
            await service.make_move(game, user, last.city_name)
        except CityAlreadyUsed:
            pass
        else:
            raise AssertionError("повтор города не отвергнут")

        starter_norm = normalize_city(last.city_name)
        answer = await _pick_user_answer(service, required, starter_norm)
        if answer is None:
            raise AssertionError(
                f"нет хода для пользователя на букву «{required}» "
                f"(стартер «{last.city_name}»)"
            )

        need_after_user = last_letter(answer)
        result = await service.make_move(game, user, answer)
        await session.commit()

        bot_city = result.bot_city.name if result.bot_city else None
        if not bot_city:
            raise AssertionError(
                f"бот не ответил городом на букву «{need_after_user}» "
                f"(после хода «{answer}»)"
            )
        expected_letter = last_letter(bot_city)
        if result.next_letter != expected_letter:
            raise AssertionError(
                f"следующая буква «{result.next_letter}», "
                f"а у города {bot_city} последняя «{expected_letter}»"
            )
        if game.moves_count != 3:
            raise ArithmeticError(f"moves_count={game.moves_count}, ожидалось 3")
        history = await moves.list_by_game(game.id)
        if len(history) != 3:
            raise ArithmeticError(f"записей о ходах={len(history)}, ожидалось 3")
        if game.score <= 0:
            raise ArithmeticError("очки за город не начислены")
        return (
            f"старт={last.city_name}, ответ={answer}, бот={bot_city}, "
            f"ходов={len(history)}, очки={game.score}, буква={result.next_letter}"
        )


async def check_geo_game() -> str:
    from app.database import async_session_factory
    from app.services.geo_game_service import GeoGameService
    from app.services.user_service import UserService

    async with async_session_factory() as session:
        user = await UserService(session).get_or_create(1_000_000_003, "hc_geo")
        service = GeoGameService(session)
        game = await service.start(user.id)
        answer = await service.check_answer(
            game,
            real_lat=55.7558,
            real_lon=37.6173,
            guess_lat=59.9343,
            guess_lon=30.3351,
        )
        await session.commit()
        distance = answer["distance_km"]
        if not 620 <= distance <= 660:
            raise ValueError(f"Москва-Петербург = {distance:.1f} км, ожидалось ~633")
        if answer["score"] <= 0:
            raise ValueError("geo-очки не начислены")
    return f"geo game={game.id}, {distance:.0f}км, очки={answer['score']}"


async def check_providers() -> str:
    from app.config import get_settings
    from app.constants import PROVIDER_CHAINS
    from app.services.external.registry import ExternalRegistry
    from app.utils.http_client import close_http_session, create_http_session

    http = create_http_session()
    try:
        registry = ExternalRegistry(http=http, settings=get_settings())
        chain = registry.chain_for("cities")
        configs = {p.name: p.is_configured for p in chain.providers}
        if not configs:
            raise AssertionError("каскад cities пуст")
        if configs.get("geonames"):
            raise AssertionError("geonames не должен быть настроен без ключа")
        if not configs.get("nominatim"):
            raise AssertionError("nominatim должен работать без ключа")
        chain.weather = registry.chain_for("weather")
        weather = {p.name: p.is_configured for p in chain.weather.providers}
        if not weather.get("open_meteo"):
            raise AssertionError("open_meteo должен работать без ключа")
    finally:
        await close_http_session()
    return f"функций={len(PROVIDER_CHAINS)}, cities={configs}, weather={weather}"


async def check_dispatcher() -> str:
    from app.bot.dispatcher import create_dispatcher
    from app.handlers.router import root_router

    dp = create_dispatcher()
    count = len(root_router.sub_routers)
    if count < 10:
        raise AssertionError(f"подключено роутеров: {count}")
    if len(dp.sub_routers) != 1:
        raise AssertionError(f"в Dispatcher должен быть один root_router, а их {len(dp.sub_routers)}")
    return f"{count} роутеров в root_router"


# ─────────────────────────── запуск ───────────────────────────

STEPS: list[tuple[str, Callable[[], Awaitable[str]]]] = [
    ("config", check_config),
    ("imports", check_imports),
    ("database", check_database),
    ("cache", check_cache),
    ("score", check_score),
    ("users", check_users),
    ("cities", check_cities),
    ("game_engine", check_game_engine),
    ("geo_game", check_geo_game),
    ("providers", check_providers),
    ("dispatcher", check_dispatcher),
]


async def main() -> int:
    """Прогнать все проверки и сохранить отчёт."""
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    for name, fn in STEPS:
        await run_step(name, fn)

    failed = [r for r in RESULTS if r["status"] == "fail"]
    report = {
        "total": len(RESULTS),
        "passed": len(RESULTS) - len(failed),
        "failed": len(failed),
        "checks": RESULTS,
    }
    (ROOT / "logs" / "healthcheck.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nИтого: {report['passed']}/{report['total']} проверок OK")
    if failed:
        print("Провалы: " + ", ".join(str(r["check"]) for r in failed))
        return 1
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
