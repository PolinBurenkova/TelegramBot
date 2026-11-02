# app/models/base.py
"""DeclarativeBase и naming convention для Alembic.

Engine и sessionmaker живут в app/database.py — здесь только метаданные.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Явные имена constraint'ов — чтобы Alembic генерировал стабильные миграции
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Реэкспорт для обратной совместимости: движок и фабрика сессий живут в
# app.database, но часть кода исторически импортирует их из app.models.base.
from app.database import (  # noqa: E402, F401
    async_engine,
    async_session_factory,
    dispose_engine,
    get_session,
    init_models,
)

__all__ = [
    "Base",
    "NAMING_CONVENTION",
    "async_engine",
    "async_session_factory",
    "dispose_engine",
    "get_session",
    "init_models",
]