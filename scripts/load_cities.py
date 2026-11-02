"""Загрузка городов из дампа GeoNames (data/cities500.txt) в таблицу cities.

Формат дампа — TSV без заголовка, 19 колонок:
    geonameid, name, asciiname, alternatenames, latitude, longitude,
    feature_class, feature_code, country_code, cc2, admin1..admin4,
    population, elevation, dem, timezone, modification_date

Скрипт берёт только населённые пункты (feature_class == "P"), отбрасывает
строки без координат, а затем пишет их в БД
через CityRepo. Уже существующие normalized_name пропускаются (эквивалент
ON CONFLICT DO NOTHING), поэтому запуск идемпотентен. Запись идёт батчами:
транзакция коммитится каждые --batch строк, а сбой одной строки не рвёт
батч (SAVEPOINT на строку). По умолчанию берутся **все страны** дампа
(фильтр `--countries` пуст) и **все** города: `CITIES_MIN_POPULATION = 0`,
ограничение по населению снято (порог можно задать явно через
`--min-population`). Названия берутся из колонки `name` дампа; для мировых
городов в русской транслитерации используйте сид
`data/seed/cities_seed.json` → `python -m scripts.seed_cities_seed`.

Запуск:
    python -m scripts.load_cities --min-population 50000
    python -m scripts.load_cities --countries RU,BY,KZ --limit 5000 --dry-run
    python -m scripts.load_cities --file data/cities500.txt --batch 1000

Код возврата 0 — данные загружены (или успешно проверены в dry-run),
1 — дамп отсутствует/пуст или произошла ошибка записи.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DUMP_PATH = ROOT / "data" / "cities500.txt"
COUNTRIES_PATH = ROOT / "data" / "countries.json"

# Индексы колонок в TSV GeoNames.
COL_ID = 0
COL_NAME = 1
COL_ALT_NAMES = 3
COL_LAT = 4
COL_LON = 5
COL_CLASS = 6
COL_FEATURE = 7
COL_COUNTRY = 8
COL_POPULATION = 14
COL_TIMEZONE = 17

MIN_FIELDS = 19


def log(message: str) -> None:
    """Печать прогресса в stdout без внешних зависимостей."""
    print(message, flush=True)


def load_country_names(path: Path) -> dict[str, str]:
    """Прочитать data/countries.json и вернуть {code: name_ru}."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    names: dict[str, str] = {}
    for item in raw:
        code = str(item.get("code", "")).strip().upper()
        name = str(item.get("name_ru") or item.get("name", "")).strip()
        if code and name:
            names[code] = name
    return names


def parse_row(
    line: str,
    *,
    country_names: dict[str, str],
    countries: set[str],
    min_population: int,
) -> dict[str, Any] | None:
    """Разобрать одну строку дампа. None — строка не подходит."""
    fields = line.rstrip("\n").split("\t")
    if len(fields) < MIN_FIELDS:
        return None
    if fields[COL_CLASS] != "P":
        return None

    name = fields[COL_NAME].strip()
    if not name:
        return None

    country_code = fields[COL_COUNTRY].strip().upper()
    if len(country_code) != 2:
        return None
    if countries and country_code not in countries:
        return None

    try:
        population = int(fields[COL_POPULATION] or 0)
    except ValueError:
        return None
    if population < min_population:
        return None

    try:
        lat = float(fields[COL_LAT])
        lon = float(fields[COL_LON])
    except ValueError:
        return None

    return {
        "name": name,
        "country_code": country_code,
        "country_name": country_names.get(country_code, ""),
        "population": population,
        "lat": lat,
        "lon": lon,
        "timezone": fields[COL_TIMEZONE].strip() or None,
        "source": "geonames",
    }


def iter_dump(
    path: Path,
    *,
    country_names: dict[str, str],
    countries: set[str],
    min_population: int,
) -> Iterator[dict[str, Any]]:
    """Потоково читать дамп и отдавать подходящие города."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = parse_row(
                line,
                country_names=country_names,
                countries=countries,
                min_population=min_population,
            )
            if row is not None:
                yield row


def dedupe(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Оставить самый населённый город на каждый normalized_name.

    Ключ совпадает с уникальным индексом таблицы cities (только
    normalized_name), поэтому в БД не будет лишних конфликтов.
    """
    from app.utils.validators import normalize_city

    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalize_city(row["name"])
        current = best.get(key)
        if current is None or row["population"] > current["population"]:
            best[key] = row
    return sorted(best.values(), key=lambda r: (-r["population"], r["name"]))


def default_min_population() -> int:
    """Порог населения по умолчанию — из app.constants (единый источник).

    Сейчас `CITIES_MIN_POPULATION = 0`, то есть по умолчанию грузятся все города
    дампа; порог можно задать явно через `--min-population`.
    """
    from app.constants import CITIES_MIN_POPULATION

    return CITIES_MIN_POPULATION


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Загрузить города из GeoNames в таблицу cities",
    )
    parser.add_argument(
        "--dump",
        "--file",
        dest="dump",
        type=Path,
        default=DUMP_PATH,
        help="путь к cities500.txt (по умолчанию data/cities500.txt)",
    )
    parser.add_argument(
        "--min-population",
        type=int,
        default=default_min_population(),
        help="минимальное население (по умолчанию 0 — без ограничения)",
    )
    parser.add_argument(
        "--countries",
        default="",
        help="коды стран через запятую (по умолчанию все страны; "
        "например RU,BY,KZ,UA — только эти)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="ограничить число городов после дедупликации (0 — без лимита)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=500,
        help="коммитить транзакцию каждые N строк (по умолчанию 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="только прочитать дамп и показать статистику, без записи в БД",
    )
    return parser.parse_args(argv)


async def write_cities(
    rows: list[dict[str, Any]],
    batch: int = 500,
) -> tuple[int, int]:
    """Записать города батчами. Возвращает (inserted, skipped)."""
    from app.database import async_session_factory, dispose_engine
    from app.models.city import City
    from app.repositories.city_repo import CityRepo
    from app.utils.validators import normalize_city

    batch = max(1, batch)
    inserted = 0
    skipped = 0
    async with async_session_factory() as session:
        repo = CityRepo(session)
        for row in rows:
            payload = {
                "name": row["name"],
                "normalized_name": normalize_city(row["name"]),
                "country_code": row["country_code"],
                "country_name": row["country_name"] or row["country_code"],
                "population": row["population"],
                "lat": row["lat"],
                "lon": row["lon"],
                "source": row["source"],
            }
            try:
                # SAVEPOINT на строку: один конфликт не ломает транзакцию.
                async with session.begin_nested():
                    exists = await repo.get_by_name(payload["name"])
                    if exists is not None:
                        skipped += 1
                        continue
                    session.add(City(**payload))
                    await session.flush()
                inserted += 1
            except Exception as exc:  # noqa: BLE001 — дамп большой, сбой строки не критичен
                skipped += 1
                log(f"  ! {payload['name']} ({row['country_code']}): {exc}")
            done = inserted + skipped
            if done % batch == 0:
                await session.commit()
                log(f"  … обработано {done} строк")
        await session.commit()
    await dispose_engine()
    return inserted, skipped


async def main(argv: list[str] | None = None) -> int:
    """Точка входа: прочитать дамп и загрузить города."""
    args = parse_args(argv)

    if not args.dump.exists():
        log(f"Нет файла дампа: {args.dump}")
        log("Скачайте его: pwsh -File scripts/download_dumps.ps1")
        return 1

    countries = {
        part.strip().upper()
        for part in args.countries.split(",")
        if part.strip()
    }
    country_names = load_country_names(COUNTRIES_PATH)
    log(
        "Читаю {0} (min_population={1}, countries={2})".format(
            args.dump.name,
            args.min_population,
            ",".join(sorted(countries)) or "all",
        )
    )

    rows = dedupe(
        iter_dump(
            args.dump,
            country_names=country_names,
            countries=countries,
            min_population=args.min_population,
        )
    )
    if args.limit > 0:
        rows = rows[: args.limit]

    if not rows:
        log("Подходящих городов не найдено. Проверьте файл дампа и фильтры.")
        return 1

    by_country: dict[str, int] = {}
    for row in rows:
        by_country[row["country_code"]] = by_country.get(row["country_code"], 0) + 1
    log(f"Готово к загрузке: {len(rows)} городов")
    for code in sorted(by_country):
        log(f"  {code}: {by_country[code]}")

    if args.dry_run:
        log("dry-run: в БД ничего не записано")
        return 0

    inserted, skipped = await write_cities(rows, batch=args.batch)
    log(f"Записано: {inserted}, пропущено (дубликаты/ошибки): {skipped}")
    return 0 if inserted > 0 or skipped == len(rows) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
