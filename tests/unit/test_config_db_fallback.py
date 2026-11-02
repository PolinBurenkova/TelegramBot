"""Юнит-тесты dev-фолбэка БД (``app/config.py``).

Если в dev-окружении задан Postgres-DSN, а порт не отвечает, настройки должны
переключаться на локальный SQLite; в production и при
``DB_FALLBACK_SQLITE=false`` — сохранять исходный URL.
"""
from __future__ import annotations

import pytest

from app.config import Settings

# Порт 1 на loopback закрыт всегда — надёжный «мёртвый» Postgres.
DEAD_PG = "postgresql+asyncpg://user:pass@127.0.0.1:1/none"
SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


def make_settings(**overrides: object) -> Settings:
    """Settings без чтения реального .env: только явные значения."""
    values: dict[str, object] = {
        "bot_token": "1:test-token",
        "environment": "development",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_dev_fallback_switches_to_sqlite_when_postgres_is_down() -> None:
    settings = make_settings(database_url=DEAD_PG)

    assert settings.db_fallback_used is True
    assert settings.database_url is not None
    assert settings.database_url.startswith("sqlite")
    assert settings.database_url == settings.db_fallback_url


def test_production_keeps_postgres_url() -> None:
    settings = make_settings(database_url=DEAD_PG, environment="production")

    assert settings.db_fallback_used is False
    assert settings.database_url == DEAD_PG


def test_fallback_can_be_disabled() -> None:
    settings = make_settings(database_url=DEAD_PG, db_fallback_sqlite=False)

    assert settings.db_fallback_used is False
    assert settings.database_url == DEAD_PG


def test_sqlite_url_is_never_rewritten() -> None:
    settings = make_settings(database_url=SQLITE_MEMORY)

    assert settings.db_fallback_used is False
    assert settings.database_url == SQLITE_MEMORY
    # SQLite in-memory по-прежнему получает StaticPool (см. async_engine_kwargs)
    assert "poolclass" in settings.async_engine_kwargs


@pytest.mark.parametrize("port", [1])
def test_closed_port_is_detected(port: int) -> None:
    assert Settings._db_port_open("127.0.0.1", port) is False
