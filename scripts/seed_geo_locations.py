"""Наполнение таблицы geo_locations из data/seed/geo_locations_seed.json.

Модель GeoLocation хранит только координаты, ссылки на картинку, страну,
сложность и источник. Поля сида title/description — витринные: они нужны
для документации и будущих миграций, в БД не пишутся.

Картинки в сиде — заглушки picsum.photos: для продакшена их надо заменить
реальными панорамами, скрипт это никак не проверяет.

Дедупликация выполняется репозиторием по (lat, lon, source), поэтому
повторный запуск не создаёт дублей.

Запуск:
    python -m scripts.seed_geo_locations
    python -m scripts.seed_geo_locations --dry-run
    python -m scripts.seed_geo_locations --allow-placeholders

Код возврата 0 — данные записаны, 1 — ошибка/невалидный сид.
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

SEED_PATH = ROOT / "data" / "seed" / "geo_locations_seed.json"
REQUIRED_FIELDS: tuple[str, ...] = ("lat", "lon", "image_url", "difficulty", "source")
ALLOWED_DIFFICULTY: frozenset[str] = frozenset({"easy", "medium", "hard"})
PLACEHOLDER_HOST = "picsum.photos"


def log(message: str) -> None:
    """Печать прогресса."""
    print(message, flush=True)


def load_seed(path: Path) -> list[dict[str, Any]]:
    """Прочитать сид и привести записи к колонкам geo_locations."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("ожидался JSON-список локаций")

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        missing = [field for field in REQUIRED_FIELDS if item.get(field) in (None, "")]
        if missing:
            raise ValueError(f"[{index}] нет полей: {', '.join(missing)}")

        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"[{index}] lat/lon не числа") from exc

        difficulty = str(item["difficulty"]).strip().lower()
        if difficulty not in ALLOWED_DIFFICULTY:
            raise ValueError(
                f"[{index}] difficulty={difficulty!r}, "
                f"ожидалось одно из {sorted(ALLOWED_DIFFICULTY)}"
            )

        country_code = item.get("country_code")
        rows.append(
            {
                "image_url": str(item["image_url"]).strip(),
                "thumb_url": (str(item["thumb_url"]).strip() if item.get("thumb_url") else None),
                "lat": lat,
                "lon": lon,
                "country_code": (str(country_code).strip().upper() if country_code else None),
                "difficulty": difficulty,
                "source": str(item["source"]).strip()[:20],
            }
        )
    return rows


def count_placeholders(rows: list[dict[str, Any]]) -> int:
    """Сколько ссылок на картинки — заглушки picsum.photos."""
    return sum(1 for row in rows if PLACEHOLDER_HOST in row["image_url"])


async def insert(rows: list[dict[str, Any]]) -> int:
    """Записать локации через GeoLocationRepo.bulk_insert."""
    from app.database import async_session_factory, dispose_engine
    from app.repositories.geo_location_repo import GeoLocationRepo

    async with async_session_factory() as session:
        repo = GeoLocationRepo(session)
        count = await repo.bulk_insert(rows)
        await session.commit()
    await dispose_engine()
    return count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Загрузить geo-локации в БД")
    parser.add_argument(
        "--seed",
        type=Path,
        default=SEED_PATH,
        help="путь к JSON сида (по умолчанию data/seed/geo_locations_seed.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="только провалидировать сид, без записи",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="разрешить запись, даже если в сиде только заглушки картинок",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    """Точка входа: загрузить geo-локации."""
    args = parse_args(argv)

    if not args.seed.exists():
        log(f"Нет файла сида: {args.seed}")
        return 1

    try:
        rows = load_seed(args.seed)
    except (ValueError, json.JSONDecodeError) as exc:
        log(f"Сид не прошёл валидацию: {exc}")
        return 1

    placeholders = count_placeholders(rows)
    log(f"Локаций в сиде: {len(rows)}, из них с картинкой-заглушкой: {placeholders}")

    if args.dry_run:
        log("dry-run: в БД ничего не записано")
        return 0

    if placeholders and not args.allow_placeholders:
        log(
            "Все картинки — заглушки picsum.photos. "
            "Для записи заглушек добавьте --allow-placeholders."
        )
        return 1

    try:
        count = await insert(rows)
    except Exception as exc:  # noqa: BLE001
        log(f"Ошибка записи: {exc}")
        return 1

    log(f"Вставлено (без дублей по координатам): {count}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
