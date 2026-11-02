"""Интеграционный тест цепочки Alembic: upgrade head -> downgrade base.

Проверяет главное свойство baseline-стратегии: 0001 создаёт ровно те таблицы,
что объявлены в app.models, а downgrade убирает всё созданное (ревизия
обратима). База — временный файл SQLite, поэтому тест ничего не трогает
в ./data и не требует Postgres.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.config import settings
from app.models import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"

pytestmark = pytest.mark.integration


@pytest.fixture()
def alembic_cfg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Config, Path]:
    """Alembic-конфиг, нацеленный на временную SQLite-базу."""
    db_path = tmp_path / "migrations.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setattr(settings, "database_url", url, raising=False)
    monkeypatch.chdir(REPO_ROOT)

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    return cfg, db_path


def _table_names(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def test_upgrade_head_creates_all_model_tables(alembic_cfg: tuple[Config, Path]) -> None:
    cfg, db_path = alembic_cfg

    command.upgrade(cfg, "head")

    tables = _table_names(db_path)
    expected = set(Base.metadata.tables)
    missing = expected - tables
    assert not missing, f"миграция не создала таблицы: {sorted(missing)}"
    assert "alembic_version" in tables


def test_downgrade_base_removes_everything(alembic_cfg: tuple[Config, Path]) -> None:
    cfg, db_path = alembic_cfg

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    leftover = _table_names(db_path) & set(Base.metadata.tables)
    assert not leftover, f"downgrade оставил таблицы: {sorted(leftover)}"


def test_chain_is_linear_and_head_is_0006() -> None:
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    heads = script.get_heads()
    assert heads == ["0006"], heads

    revisions = [rev.revision for rev in script.walk_revisions()]
    assert revisions == ["0006", "0005", "0004", "0003", "0002", "0001"], revisions
