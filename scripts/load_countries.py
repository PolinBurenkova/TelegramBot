"""Проверка справочника стран (data/countries.json + data/country_codes.json).

В моделях проекта нет таблицы countries: справочник читается сервисами
напрямую из JSON. Поэтому скрипт не «заливает» его в БД, а:

1) проверяет структуру обоих файлов (поля, типы, уникальность кодов);
2) сверяет справочник с данными БД: все ли country_code из таблицы cities
   описаны в countries.json;
3) по флагу --sync-db дописывает пустые cities.country_name по коду страны.

Запуск:
    python -m scripts.load_countries --check
    python -m scripts.load_countries --check --sync-db

Код возврата 0 — справочник согласован (и синхронизация выполнена),
1 — найдены расхождения или ошибка записи.
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

COUNTRIES_PATH = ROOT / "data" / "countries.json"
CODES_PATH = ROOT / "data" / "country_codes.json"
REPORT_PATH = ROOT / "logs" / "load_countries.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "code",
    "iso3",
    "name_ru",
    "name_en",
    "capital",
    "population",
    "region",
    "currency",
    "languages",
    "lat",
    "lon",
    "timezones",
)


def log(message: str) -> None:
    """Печать строки отчёта."""
    print(message, flush=True)


def read_json(path: Path) -> Any:
    """Прочитать JSON-файл в UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def check_countries(raw: list[dict[str, Any]]) -> list[str]:
    """Вернуть список найденных проблем в countries.json."""
    problems: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        code = str(item.get("code", "")).strip().upper()
        if len(code) != 2:
            problems.append(f"[{index}] некорректный code={code!r}")
            continue
        if code in seen:
            problems.append(f"[{index}] дубликат code={code}")
        seen.add(code)
        for field in REQUIRED_FIELDS:
            if field not in item:
                problems.append(f"{code}: нет поля {field}")
        iso3 = str(item.get("iso3", "")).strip().upper()
        if len(iso3) != 3 or not iso3.isalpha():
            problems.append(f"{code}: некорректный iso3={iso3!r}")
        if not str(item.get("name_ru", "")).strip():
            problems.append(f"{code}: пустое name_ru")
        if not str(item.get("name_en", "")).strip():
            problems.append(f"{code}: пустое name_en")
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            problems.append(f"{code}: lat/lon не числа")
        else:
            if not -90.0 <= lat <= 90.0:
                problems.append(f"{code}: lat={lat} вне диапазона")
            if not -180.0 <= lon <= 180.0:
                problems.append(f"{code}: lon={lon} вне диапазона")
        zones = item.get("timezones")
        if not isinstance(zones, list) or not zones:
            problems.append(f"{code}: timezones должен быть непустым списком")
    return problems


def check_codes(
    raw: dict[str, Any],
    countries: list[dict[str, Any]],
) -> list[str]:
    """Проверить карту «ISO2 → iso3/numeric/dial_code» из country_codes.json."""
    problems: list[str] = []
    iso3_by_code: dict[str, str] = {}
    for item in countries:
        code = str(item.get("code", "")).strip().upper()
        if code:
            iso3_by_code[code] = str(item.get("iso3", "")).strip().upper()
    seen: set[str] = set()
    for code, payload in raw.items():
        key = str(code).strip().upper()
        if len(key) != 2:
            problems.append(f"ключ {code!r} не ISO2-код")
            continue
        if key in seen:
            problems.append(f"дубликат ключа {key}")
        seen.add(key)
        if key not in iso3_by_code:
            problems.append(f"{key}: нет такой страны в countries.json")
        if not isinstance(payload, dict):
            problems.append(f"{key}: ожидался объект с iso3/numeric/dial_code")
            continue
        iso3 = str(payload.get("iso3", "")).strip().upper()
        if len(iso3) != 3 or not iso3.isalpha():
            problems.append(f"{key}: некорректный iso3={iso3!r}")
        elif key in iso3_by_code and iso3_by_code[key] != iso3:
            expected = iso3_by_code[key]
            problems.append(f"{key}: iso3={iso3} расходится с countries.json ({expected})")
        numeric = str(payload.get("numeric", "")).strip()
        if not (numeric.isdigit() and len(numeric) == 3):
            problems.append(f"{key}: numeric={numeric!r} должен быть трёхзначным числом")
        dial = str(payload.get("dial_code", "")).strip()
        if not (dial.startswith("+") and dial[1:].isdigit()):
            problems.append(f"{key}: dial_code={dial!r} должен начинаться с «+»")
    for key in sorted(set(iso3_by_code) - seen):
        problems.append(f"{key}: нет записи в country_codes.json")
    return problems


async def check_db(country_names: dict[str, str]) -> list[str]:
    """Сверить country_code из таблицы cities со справочником."""
    from sqlalchemy import distinct, select

    from app.database import async_session_factory, dispose_engine
    from app.models.city import City

    problems: list[str] = []
    async with async_session_factory() as session:
        rows = await session.execute(select(distinct(City.country_code)))
        db_codes = {str(code).strip().upper() for code in rows.scalars().all() if code}
    await dispose_engine()

    for code in sorted(db_codes):
        if code not in country_names:
            problems.append(f"БД: country_code={code} отсутствует в countries.json")
    log(f"Кодов стран в БД (cities): {len(db_codes)}")
    return problems


async def sync_db(country_names: dict[str, str], dry_run: bool) -> int:
    """Заполнить пустые cities.country_name по коду страны."""
    from sqlalchemy import or_, select, update

    from app.database import async_session_factory, dispose_engine
    from app.models.city import City

    updated = 0
    async with async_session_factory() as session:
        rows = await session.execute(
            select(City.id, City.country_code).where(
                or_(City.country_name.is_(None), City.country_name == "")
            )
        )
        targets = [(city_id, code) for city_id, code in rows.all() if code]
        if dry_run:
            log(f"dry-run: стран без названия — {len(targets)}, изменений не будет")
            await dispose_engine()
            return len(targets)
        for city_id, code in targets:
            name = country_names.get(str(code).strip().upper())
            if not name:
                continue
            await session.execute(
                update(City).where(City.id == city_id).values(country_name=name)
            )
            updated += 1
        await session.commit()
    await dispose_engine()
    log(f"Обновлено cities.country_name: {updated}")
    return updated


def write_report(payload: dict[str, Any]) -> None:
    """Сохранить отчёт в logs/load_countries.json."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Проверка справочника стран")
    parser.add_argument(
        "--check",
        action="store_true",
        help="проверить структуру файлов и согласованность с БД (по умолчанию)",
    )
    parser.add_argument(
        "--sync-db",
        action="store_true",
        help="заполнить пустые cities.country_name из справочника",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="не писать изменения в БД",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    """Точка входа: проверить справочник и при необходимости синхронизировать БД."""
    args = parse_args(argv)

    for path in (COUNTRIES_PATH, CODES_PATH):
        if not path.exists():
            log(f"Нет файла: {path}")
            return 1

    raw_countries = read_json(COUNTRIES_PATH)
    raw_codes = read_json(CODES_PATH)
    if not isinstance(raw_countries, list) or not isinstance(raw_codes, dict):
        log("Неожиданный формат JSON: ожидались список и словарь")
        return 1

    country_names = {
        str(item.get("code", "")).strip().upper(): str(
            item.get("name_ru") or item.get("name", "")
        ).strip()
        for item in raw_countries
        if item.get("code")
    }
    log(f"Стран в справочнике: {len(raw_countries)}")

    problems = check_countries(raw_countries)
    problems.extend(check_codes(raw_codes, raw_countries))
    log(f"Записей в country_codes.json: {len(raw_codes)}")

    problems.extend(await check_db(country_names))

    updated = 0
    if args.sync_db:
        updated = await sync_db(country_names, dry_run=args.dry_run)

    write_report(
        {
            "countries": len(raw_countries),
            "codes": len(raw_codes),
            "problems": problems,
            "synced_rows": updated,
        }
    )
    if problems:
        for problem in problems:
            log(f"  ! {problem}")
        log(f"Расхождений: {len(problems)}")
        return 1
    log("Справочник стран согласован")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
