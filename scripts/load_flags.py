"""Проверка справочника флагов (data/flags.json).

Таблицы flags в моделях нет: флаги нужны только UI (emoji + ссылки на SVG/PNG),
поэтому скрипт проверяет ассет, а не пишет строки в БД:

1) у каждой записи есть code/name/name_en/emoji/svg_url/png_url/source;
2) code уникален и присутствует в data/countries.json;
3) URL-шаблоны указывают на flagcdn.com и содержат тот же код страны;
4) все страны из справочника имеют флаг (обратное покрытие).

Запуск:
    python -m scripts.load_flags
    python -m scripts.load_flags --strict   # расхождение покрытия — ошибка

Код возврата 0 — ассет корректен, 1 — найдены проблемы (или --strict покрытия).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FLAGS_PATH = ROOT / "data" / "flags.json"
COUNTRIES_PATH = ROOT / "data" / "countries.json"
REPORT_PATH = ROOT / "logs" / "load_flags.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "code",
    "name",
    "name_en",
    "emoji",
    "svg_url",
    "png_url",
    "source",
)
EXPECTED_HOST = "flagcdn.com"


def log(message: str) -> None:
    """Печать строки отчёта."""
    print(message, flush=True)


def read_json(path: Path) -> Any:
    """Прочитать JSON-файл в UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def check_flags(
    raw: list[dict[str, Any]],
    country_codes: set[str],
) -> tuple[list[str], set[str]]:
    """Вернуть (список проблем, множество кодов с флагом)."""
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
            if not str(item.get(field, "")).strip():
                problems.append(f"{code}: пустое поле {field}")
        if country_codes and code not in country_codes:
            problems.append(f"{code}: нет такой страны в countries.json")

        for field in ("svg_url", "png_url"):
            url = str(item.get(field, ""))
            if not url.startswith("https://"):
                problems.append(f"{code}: {field} должен быть https-ссылкой")
            if EXPECTED_HOST not in url:
                problems.append(f"{code}: {field} не с {EXPECTED_HOST}")
            if f"/{code.lower()}." not in url.lower():
                problems.append(f"{code}: {field} не содержит код страны")

        source = str(item.get("source", "")).strip().lower()
        if source and source != EXPECTED_HOST:
            problems.append(f"{code}: source={source!r}, ожидался {EXPECTED_HOST!r}")
    return problems, seen


def write_report(payload: dict[str, Any]) -> None:
    """Сохранить отчёт в logs/load_flags.json."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Проверка справочника флагов")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="считать ошибкой отсутствие флага у страны из countries.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Точка входа: проверить flags.json."""
    args = parse_args(argv)

    if not FLAGS_PATH.exists():
        log(f"Нет файла: {FLAGS_PATH}")
        return 1

    raw = read_json(FLAGS_PATH)
    if not isinstance(raw, list):
        log("Неожиданный формат flags.json: ожидался список")
        return 1

    country_codes: set[str] = set()
    if COUNTRIES_PATH.exists():
        countries = read_json(COUNTRIES_PATH)
        if isinstance(countries, list):
            country_codes = {
                str(item.get("code", "")).strip().upper()
                for item in countries
                if item.get("code")
            }

    problems, seen = check_flags(raw, country_codes)
    missing = sorted(country_codes - seen)
    if missing:
        message = "Нет флага у стран: " + ", ".join(missing)
        if args.strict:
            problems.append(message)
        else:
            log(f"  i {message}")

    log(f"Флагов: {len(raw)}, стран в справочнике: {len(country_codes)}")
    write_report(
        {
            "flags": len(raw),
            "countries": len(country_codes),
            "missing": missing,
            "problems": problems,
        }
    )
    if problems:
        for problem in problems:
            log(f"  ! {problem}")
        log(f"Проблем: {len(problems)}")
        return 1
    log("Справочник флагов корректен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
