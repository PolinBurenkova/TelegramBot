"""Полный сброс схемы БД: удаление всех таблиц и создание заново.

Скрипт destructive: без флага --yes он только показывает, какие таблицы
будут удалены, и завершается с кодом 1. Данные пользователей, игр и
кэша при сбросе теряются безвозвратно.

Запуск:
    python -m scripts.reset_db                # только показать план
    python -m scripts.reset_db --yes          # пересоздать пустую схему
    python -m scripts.reset_db --yes --with-seed   # плюс сид-данные

Код возврата 0 — схема пересоздана (или показан план при --dry-run),
1 — нет --yes или произошла ошибка.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def log(message: str) -> None:
    """Печать прогресса."""
    print(message, flush=True)


async def recreate_schema() -> list[str]:
    """Удалить и создать все таблицы. Возвращает список имён таблиц."""
    from app.database import async_engine, dispose_engine, init_models
    from app.models.base import Base

    names = sorted(Base.metadata.tables)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    log("Таблицы удалены")
    await init_models()
    log("Схема создана заново")
    await dispose_engine()
    return names


async def run_seed() -> None:
    """Загрузить сид-данные после пересоздания схемы."""
    from scripts.seed_achievements import load_seed as load_achievements
    from scripts.seed_achievements import upsert as upsert_achievements
    from scripts.seed_cities_seed import insert as insert_cities
    from scripts.seed_cities_seed import load_seed as load_cities

    achievements = load_achievements(ROOT / "data" / "seed" / "achievements_seed.json")
    log(f"Достижений к загрузке: {len(achievements)}")
    await upsert_achievements(achievements)

    cities = load_cities(ROOT / "data" / "seed" / "cities_seed.json")
    inserted, skipped = await insert_cities(cities)
    log(f"Городов вставлено: {inserted}, пропущено: {skipped}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Полный сброс схемы БД")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="подтвердить удаление всех данных",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="только показать план, ничего не удалять",
    )
    parser.add_argument(
        "--with-seed",
        action="store_true",
        help="после пересоздания схемы загрузить сид-данные",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    """Точка входа: сбросить схему БД."""
    from app.models.base import Base

    args = parse_args(argv)
    tables = sorted(Base.metadata.tables)

    log(f"Таблиц в метаданных: {len(tables)}")
    for name in tables:
        log(f"  - {name}")

    if args.dry_run:
        log("dry-run: ничего не удалено")
        return 0

    if not args.yes:
        log("Отказ: сброс удалит все данные. Запустите с флагом --yes.")
        return 1

    try:
        await recreate_schema()
        if args.with_seed:
            await run_seed()
    except Exception as exc:  # noqa: BLE001
        log(f"Ошибка сброса: {exc}")
        return 1

    log("Готово")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
