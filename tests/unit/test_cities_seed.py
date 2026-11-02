"""Проверка сида городов `data/seed/cities_seed.json`.

Сид используется локальной игрой и `scripts/seed_cities_seed.py`, поэтому
проверяем структуру (плоский список объектов), обязательные поля, отсутствие
дубликатов после нормализации и покрытие мировых городов.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.utils.validators import normalize_city

SEED = Path(__file__).resolve().parents[2] / "data" / "seed" / "cities_seed.json"
MIRROR = Path(__file__).resolve().parents[2] / "app" / "data" / "cities_seed.json"
REQUIRED = ("name", "country_code", "country_name", "population", "lat", "lon")


def load_rows() -> list[dict]:
    raw = json.loads(SEED.read_text(encoding="utf-8"))
    assert isinstance(raw, list) and raw, "сид должен быть непустым списком"
    return raw


def test_seed_is_flat_list_of_objects() -> None:
    rows = load_rows()

    assert all(isinstance(row, dict) for row in rows), "вложенные массивы в сиде"
    assert all(isinstance(row.get("name"), str) for row in rows)


def test_required_fields_are_present() -> None:
    for index, row in enumerate(load_rows()):
        missing = [field for field in REQUIRED if row.get(field) in (None, "")]
        assert not missing, f"[{index}] {row.get('name')}: нет полей {missing}"


def test_names_are_unique_after_normalization() -> None:
    names = [normalize_city(row["name"]) for row in load_rows()]

    assert len(names) == len(set(names))


def test_seed_contains_world_cities() -> None:
    rows = load_rows()
    codes = {row["country_code"] for row in rows}

    assert "RU" in codes
    assert len(codes) >= 50, f"стран в сиде: {len(codes)}"
    assert len(codes - {"RU", "BY", "KZ", "UA"}) >= 40


def test_seed_covers_rare_start_letters() -> None:
    letters = {normalize_city(row["name"])[0] for row in load_rows()}

    assert {"й", "ц", "щ", "э", "я"} <= letters


def test_app_data_mirror_matches_seed() -> None:
    """Копия в app/data должна совпадать с data/seed (её читают другие скрипты)."""
    assert MIRROR.read_bytes() == SEED.read_bytes()
