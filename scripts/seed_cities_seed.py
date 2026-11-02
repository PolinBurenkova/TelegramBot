"""Наполнение таблицы cities из data/seed/cities_seed.json.

Сид — проверочный набор городов мира в русской транслитерации (112 записей,
70 стран): 26 российских городов и 86 зарубежных (Париж, Лондон, Токио,
Йоханнесбург, Цюрих и др.). Он нужен для локальной игры без полного дампа
GeoNames и даёт боту города на редкие буквы («й», «ц», «щ», «э», «я»).
В отличие от load_cities.py, здесь нет потокового парсинга TSV: файл
маленький и читается целиком.

normalized_name считается через app.utils.validators.normalize_city,
дубликаты внутри сида отбрасываются до записи, а уже существующие в БД
города пропускаются (проверка по normalized_name в SAVEPOINT).

Запуск:
    python -m scripts.seed_cities_seed
    python -m scripts.seed_cities_seed --dry-run

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

SEED_PATH = ROOT / "data" / "seed" / "cities_seed.json"
REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "country_code",
    "country_name",
    "population",
    "lat",
    "lon",
)


def log(message: str) -> None:
    """Печать прогресса."""
    print(message, flush=True)


def load_seed(path: Path) -> list[dict[str, Any]]:
    """Прочитать сид и привести записи к колонкам таблицы cities."""
    from app.utils.validators import normalize_city

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("ожидался JSON-список городов")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        missing = [field for field in REQUIRED_FIELDS if item.get(field) in (None, "")]
        if missing:
            raise ValueError(f"[{index}] нет полей: {', '.join(missing)}")

        name = str(item["name"]).strip()
        normalized = normalize_city(name)
        if not normalized:
            raise ValueError(f"[{index}] имя города пустое после нормализации")
        if normalized in seen:
            log(f"  i {name}: дубликат в сиде, пропущен")
            continue
        seen.add(normalized)

        country_code = str(item["country_code"]).strip().upper()
        if len(country_code) != 2:
            raise ValueError(f"[{index}] некорректный country_code={country_code!r}")

        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"[{index}] lat/lon не числа") from exc
        if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
            raise ValueError(f"[{index}] координаты вне допустимого диапазона")

        rows.append(
            {
                "name": name,
                "normalized_name": normalized,
                "country_code": country_code,
                "country_name": str(item["country_name"]).strip(),
                "region": (str(item["region"]).strip() if item.get("region") else None),
                "population": int(item["population"] or 0),
                "lat": lat,
                "lon": lon,
                "source": str(item.get("source") or "seed").strip()[:20],
            }
        )
    return rows


async def insert(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Записать города. Возвращает (inserted, skipped)."""
    from app.database import async_session_factory, dispose_engine
    from app.models.city import City
    from app.repositories.city_repo import CityRepo

    inserted = 0
    skipped = 0
    async with async_session_factory() as session:
        repo = CityRepo(session)
        for row in rows:
            try:
                # SAVEPOINT на строку: конфликт уникальности не рушит транзакцию.
                async with session.begin_nested():
                    exists = await repo.get_by_name(row["name"])
                    if exists is not None:
                        skipped += 1
                        continue
                    session.add(City(**row))
                    await session.flush()
                inserted += 1
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                log(f"  ! {row['name']}: {exc}")
        await session.commit()
    await dispose_engine()
    return inserted, skipped


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Загрузить сид-города в БД")
    parser.add_argument(
        "--seed",
        type=Path,
        default=SEED_PATH,
        help="путь к JSON сида (по умолчанию data/seed/cities_seed.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="только провалидировать сид, без записи",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    """Точка входа: загрузить сид-города."""
    args = parse_args(argv)

    if not args.seed.exists():
        log(f"Нет файла сида: {args.seed}")
        return 1

    try:
        rows = load_seed(args.seed)
    except (ValueError, json.JSONDecodeError) as exc:
        log(f"Сид не прошёл валидацию: {exc}")
        return 1

    countries = sorted({row["country_code"] for row in rows})
    log(f"Городов в сиде: {len(rows)} (страны: {', '.join(countries)})")

    if args.dry_run:
        log("dry-run: в БД ничего не записано")
        return 0

    try:
        inserted, skipped = await insert(rows)
    except Exception as exc:  # noqa: BLE001
        log(f"Ошибка записи: {exc}")
        return 1

    log(f"Вставлено: {inserted}, пропущено: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
