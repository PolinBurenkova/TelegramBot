# tests/conftest.py
"""Корневая конфигурация pytest для проекта «Города+».

Принципы:
- полностью офлайн: ни Telegram, ни реальных Postgres/Redis, ни HTTP-вызовов;
- имена фикстур — часть общего контракта тестов, переименовывать нельзя;
- тестовая БД — SQLite в памяти (aiosqlite), схема создаётся из метаданных моделей;
- реальный `.env` не требуется: тестовые значения задаются через переменные окружения
  до первого импорта `app.config` (переменные окружения приоритетнее `.env`).
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path

# Корень репозитория в sys.path: `tests/pytest.ini` делает rootdir = tests/,
# поэтому настройка `pythonpath` из корневого pyproject.toml не применяется,
# и без этой строки `pytest` (консольный скрипт, не `python -m pytest`) не смог
# бы импортировать пакет `app`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ВАЖНО: окружение готовится до импорта app.config.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("BOT_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("ADMIN_IDS", "1")
# Redis-адреса обнуляем принудительно: иначе значение из окружения разработчика
# увело бы кэш/лимиты на реальный сервер, а unit-тесты должны быть офлайн.
os.environ["REDIS_URL"] = ""
os.environ["FSM_REDIS_URL"] = ""

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fakeredis.aioredis import FakeRedis  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings  # noqa: E402
from app.config import settings as app_settings  # noqa: E402
from app.models import Base, City, User  # noqa: E402
from app.utils.validators import normalize_city  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_TG_ID = 1_000_000_002


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Синглтон настроек, переключённый на тестовую БД.

    Фикстура `monkeypatch` имеет function-scope, поэтому для session-scope
    создаём отдельный экземпляр `pytest.MonkeyPatch` и снимаем патчи в teardown.
    """
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(app_settings, "database_url", TEST_DATABASE_URL)
    monkeypatch.setattr(app_settings, "environment", "test")
    try:
        yield app_settings
    finally:
        monkeypatch.undo()


@pytest_asyncio.fixture
async def session_factory(
    settings: Settings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Фабрика сессий над свежей in-memory SQLite с созданной схемой."""
    engine: AsyncEngine = create_async_engine(
        settings.database_url or TEST_DATABASE_URL,
        **settings.async_engine_kwargs,
    )
    factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Готовая сессия БД. Изменения откатываются после теста."""
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[FakeRedis]:
    """In-memory замена Redis (fakeredis) с декодированием строк."""
    redis = FakeRedis(decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Сохранённый пользователь с реальными полями модели `User`."""
    user = User(
        tg_id=TEST_TG_ID,
        username="test_user",
        first_name="Тест",
        language="ru",
        locale="ru",
        total_score=0,
        level=0,
        difficulty="easy",
        show_weather=True,
        show_photo=True,
        notify=True,
        is_banned=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_city(db_session: AsyncSession) -> City:
    """Сохранённый город из справочника (Москва)."""
    name = "Москва"
    city = City(
        name=name,
        normalized_name=normalize_city(name),
        country_code="RU",
        country_name="Россия",
        region="Москва",
        population=13_000_000,
        lat=55.7558,
        lon=37.6173,
        source="test",
    )
    db_session.add(city)
    await db_session.commit()
    await db_session.refresh(city)
    return city


def _default_handler(request: httpx.Request) -> httpx.Response:
    """Ответ по умолчанию для MockTransport: 200 {"ok": true}."""
    return httpx.Response(200, json={"ok": True})


@pytest_asyncio.fixture
async def mock_http() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP-клиент на httpx.MockTransport: сеть не используется."""
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_default_handler),
        base_url="https://mock.local",
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def mock_http_factory() -> AsyncIterator[Callable[..., httpx.AsyncClient]]:
    """Фабрика клиентов со своим обработчиком (для проверки разбора ответов)."""
    clients: list[httpx.AsyncClient] = []

    def make(
        handler: Callable[[httpx.Request], httpx.Response],
        *,
        base_url: str = "https://mock.local",
    ) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=base_url,
        )
        clients.append(client)
        return client

    try:
        yield make
    finally:
        for client in clients:
            await client.aclose()
