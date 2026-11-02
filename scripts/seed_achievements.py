"""Наполнение таблицы achievements из data/seed/achievements_seed.json.

Сид-файл содержит поля code / name / description / icon / condition.
В модели Achievement поле называется title, а condition — это условие
разблокировки, которое живёт в коде (app/constants.py), а не в БД.
Поэтому скрипт маппит name → title и отбрасывает condition.

Запись идёт через AchievementRepo.bulk_upsert: строка ищется по code и
обновляется, если уже существует, — запуск идемпотентен и не затирает
пользовательские связи user_achievements.

Запуск:
    python -m scripts.seed_achievements
    python -m scripts.seed_achievements --dry-run

Код возврата 0 — данные записаны (или проверены), 1 — ошибка.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED_PATH = ROOT / "data" / "seed" / "achievements_seed.json"
REQUIRED_FIELDS: tuple[str, ...] = ("code", "name", "description", "icon")


def log(message: str) -> None:
    """Печать прогресса."""
    print(message, flush=True)


def load_seed(path: Path) -> list[dict[str, Any]]:
    """Прочитать сид и привести записи к колонкам таблицы achievements."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("ожидался JSON-список достижений")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        missing = [field for field in REQUIRED_FIELDS if not str(item.get(field, "")).strip()]
        if missing:
            raise ValueError(f"[{index}] нет полей: {', '.join(missing)}")
        code = str(item["code"]).strip()
        if code in seen:
            raise ValueError(f"дубликат code={code}")
        seen.add(code)
        rows.append(
            {
                "code": code,
                "title": str(item["name"]).strip(),
                "description": str(item["description"]).strip(),
                "icon": str(item["icon"]).strip(),
            }
        )
    return rows


def cross_check_constants(rows: list[dict[str, Any]]) -> list[str]:
    """Сверить коды сида с ACHIEVEMENTS из app/constants.py."""
    from app.constants import ACHIEVEMENTS, ACHIEVEMENTS_REQUIREMENTS

    problems: list[str] = []
    seed_codes = {row["code"] for row in rows}
    known = set(ACHIEVEMENTS) | set(ACHIEVEMENTS_REQUIREMENTS)
    for code in sorted(seed_codes - known):
        problems.append(f"{code}: нет в ACHIEVEMENTS/ACHIEVEMENTS_REQUIREMENTS")
    for code in sorted(known - seed_codes):
        problems.append(f"{code}: есть в app/constants.py, но отсутствует в сиде")
    return problems


async def upsert(rows: list[dict[str, Any]]) -> int:
    """Записать достижения через AchievementRepo.bulk_upsert."""
    from app.database import async_session_factory, dispose_engine
    from app.repositories.achievement_repo import AchievementRepo

    async with async_session_factory() as session:
        repo = AchievementRepo(session)
        count = await repo.bulk_upsert(rows)
        await session.commit()
    await dispose_engine()
    return count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Загрузить достижения в БД")
    parser.add_argument(
        "--seed",
        type=Path,
        default=SEED_PATH,
        help="путь к JSON сида (по умолчанию data/seed/achievements_seed.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="проверить сид и сверку с app/constants.py без записи",
    )
    parser.add_argument(
        "--skip-constants-check",
        action="store_true",
        help="не сверять коды с app/constants.py",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    """Точка входа: загрузить достижения."""
    args = parse_args(argv)

    if not args.seed.exists():
        log(f"Нет файла сида: {args.seed}")
        return 1

    try:
        rows = load_seed(args.seed)
    except (ValueError, json.JSONDecodeError) as exc:
        log(f"Сид не прошёл валидацию: {exc}")
        return 1
    log(f"Достижений в сиде: {len(rows)}")

    problems = [] if args.skip_constants_check else cross_check_constants(rows)
    for problem in problems:
        log(f"  ! {problem}")

    if args.dry_run:
        log("dry-run: в БД ничего не записано")
        return 1 if problems else 0

    try:
        count = await upsert(rows)
    except Exception as exc:  # noqa: BLE001 — наверх нужен код возврата, а не трейс
        log(f"Ошибка записи: {exc}")
        return 1

    log(f"Обработано записей: {count}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
