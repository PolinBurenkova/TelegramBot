

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

async_engine: AsyncEngine = create_async_engine(
    settings.database_url or "",
    **settings.async_engine_kwargs,  # type: ignore[arg-type]
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI/aiogram-style dependency: одна сессия на запрос/хендлер."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Graceful shutdown: закрыть пул соединений."""
    await async_engine.dispose()


async def init_models() -> None:
    """Создать все таблицы из метаданных (идемпотентно).

    Путь для разработки/CI: быстрая гарантия схемы без Alembic.
    В production применяется Alembic (см. migrations/).
    """
    from app.models import Base  # noqa: PLC0415 — импорт после загрузки модуля

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def database_hint(exc: BaseException | None = None) -> str:
    """Что делать при недоступной БД (готовая строка для лога/консоли).

    Классические случаи: PostgreSQL не запущен (``ConnectionRefusedError`` /
    ``[WinError 1225]``), неверный пароль или БД ещё не создана.
    """
    return (
        "База данных недоступна"
        + (f": {exc}" if exc else "")
        + ". Варианты: (1) поднять Postgres — `docker compose up -d postgres` "
        "или запустить системную службу PostgreSQL, затем `alembic upgrade head`; "
        "(2) вернуться на локальный SQLite — "
        "`DATABASE_URL=sqlite+aiosqlite:///./data/cities_bot.db` в .env "
        "(файл data/cities_bot.db уже существует); "
        "(3) для dev можно оставить DB_FALLBACK_SQLITE=true (по умолчанию) — "
        "тогда при недоступном Postgres приложение само перейдёт на SQLite."
    )