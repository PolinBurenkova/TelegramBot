"""Проверка справочника часовых поясов (data/timezones.json).

Таблицы timezones в моделях нет — справочник используется сервисами
напрямую из JSON. Скрипт проверяет:

1) обязательные поля записи: tz, country_code, utc_offset, dst,
   abbreviation, cities;
2) уникальность tz и корректность смещения вида +03:00 / -05:00;
3) наличие country_code в data/countries.json;
4) двустороннюю согласованность со списками timezones у стран.

Запуск:
    python -m scripts.load_timezones
    python -m scripts.load_timezones --strict   # расхождения стран — ошибка

Код возврата 0 — справочник корректен, 1 — найдены проблемы.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TIMEZONES_PATH = ROOT / "data" / "timezones.json"
COUNTRIES_PATH = ROOT / "data" / "countries.json"
REPORT_PATH = ROOT / "logs" / "load_timezones.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "tz",
    "country_code",
    "utc_offset",
    "dst",
    "abbreviation",
    "cities",
)
OFFSET_RE = re.compile(r"^[+-]\d{2}:\d{2}$")


def log(message: str) -> None:
    """Печать строки отчёта."""
    print(message, flush=True)


def read_json(path: Path) -> Any:
    """Прочитать JSON-файл в UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def check_entries(raw: list[dict[str, Any]], country_codes: set[str]) -> list[str]:
    """Вернуть список проблем в timezones.json."""
    problems: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        tz = str(item.get("tz", "")).strip()
        if not tz:
            problems.append(f"[{index}] пустой tz")
            continue
        if tz in seen:
            problems.append(f"{tz}: дубликат")
        seen.add(tz)

        for field in REQUIRED_FIELDS:
            if field not in item:
                problems.append(f"{tz}: нет поля {field}")

        code = str(item.get("country_code", "")).strip().upper()
        if len(code) != 2:
            problems.append(f"{tz}: некорректный country_code={code!r}")
        elif country_codes and code not in country_codes:
            problems.append(f"{tz}: страны {code} нет в countries.json")

        offset = str(item.get("utc_offset", "")).strip()
        if not OFFSET_RE.match(offset):
            problems.append(f"{tz}: utc_offset={offset!r}, ожидался ±HH:MM")
        else:
            hours = int(offset[1:3])
            minutes = int(offset[4:6])
            if hours > 14 or minutes > 59:
                problems.append(f"{tz}: utc_offset={offset} вне диапазона")

        if not isinstance(item.get("dst"), bool):
            problems.append(f"{tz}: dst должен быть true/false")
        if not str(item.get("abbreviation", "")).strip():
            problems.append(f"{tz}: пустая abbreviation")

        cities = item.get("cities")
        if not isinstance(cities, list) or not cities:
            problems.append(f"{tz}: cities должен быть непустым списком")
        elif any(not isinstance(city, str) or not city.strip() for city in cities):
            problems.append(f"{tz}: в cities пустые или нестроковые значения")
    return problems


def check_country_lists(
    raw: list[dict[str, Any]],
    countries: list[dict[str, Any]],
) -> list[str]:
    """Сверить timezones.json со списками timezones у стран."""
    problems: list[str] = []
    by_country: dict[str, set[str]] = {}
    for item in raw:
        code = str(item.get("country_code", "")).strip().upper()
        tz = str(item.get("tz", "")).strip()
        if code and tz:
            by_country.setdefault(code, set()).add(tz)

    for country in countries:
        code = str(country.get("code", "")).strip().upper()
        declared = country.get("timezones")
        if not isinstance(declared, list):
            continue
        declared_set = {str(item).strip() for item in declared if str(item).strip()}
        actual = by_country.get(code, set())
        for tz in sorted(declared_set - actual):
            problems.append(f"{code}: {tz} указан у страны, но нет в timezones.json")
        for tz in sorted(actual - declared_set):
            problems.append(f"{code}: {tz} есть в timezones.json, но не указан у страны")
    return problems


def write_report(payload: dict[str, Any]) -> None:
    """Сохранить отчёт в logs/load_timezones.json."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Проверка справочника часовых поясов")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="считать ошибкой расхождения со списками timezones у стран",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Точка входа: проверить timezones.json."""
    args = parse_args(argv)

    if not TIMEZONES_PATH.exists():
        log(f"Нет файла: {TIMEZONES_PATH}")
        return 1

    raw = read_json(TIMEZONES_PATH)
    if not isinstance(raw, list):
        log("Неожиданный формат timezones.json: ожидался список")
        return 1

    countries: list[dict[str, Any]] = []
    country_codes: set[str] = set()
    if COUNTRIES_PATH.exists():
        loaded = read_json(COUNTRIES_PATH)
        if isinstance(loaded, list):
            countries = [item for item in loaded if isinstance(item, dict)]
            country_codes = {
                str(item.get("code", "")).strip().upper()
                for item in countries
                if item.get("code")
            }

    problems = check_entries(raw, country_codes)
    consistency = check_country_lists(raw, countries)
    if consistency and args.strict:
        problems.extend(consistency)
    else:
        for message in consistency:
            log(f"  i {message}")

    countries_seen = {
        str(item.get("country_code", "")).strip().upper()
        for item in raw
        if item.get("country_code")
    }
    log(
        "Поясов: {0}, стран с поясами: {1}, стран в справочнике: {2}".format(
            len(raw), len(countries_seen), len(country_codes)
        )
    )
    write_report(
        {
            "timezones": len(raw),
            "countries_with_timezones": sorted(countries_seen),
            "consistency_issues": consistency,
            "problems": problems,
        }
    )
    if problems:
        for problem in problems:
            log(f"  ! {problem}")
        log(f"Проблем: {len(problems)}")
        return 1
    log("Справочник часовых поясов корректен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
