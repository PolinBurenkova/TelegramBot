"""City name + coordinate validators + letter helpers."""
from __future__ import annotations

import re

from app.constants import LETTER_ALIASES, SKIPPABLE_LAST_LETTERS

CITY_RE = re.compile(r"^[А-Яа-яЁёA-Za-z][А-Яа-яЁёA-Za-z\s\-]{1,49}$")
COORD_RE = re.compile(r"^(-?\d{1,2}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)$")


def normalize_city(name: str) -> str:
    """Lowercase, ё→е, trim, collapse spaces."""
    s = name.strip().lower().replace("ё", "е")
    return re.sub(r"\s+", " ", s)


def last_letter(city: str) -> str:
    """Буква, с которой должен начинаться следующий город.

    Отбрасываются только «немые» окончания ь/ъ/ы (с них не начинается ни один
    город). «й» остаётся рабочей буквой: «Волжский» → следующий на «й».
    «ё» приводится к «е».
    """
    c = re.sub(r"[\s\-]", "", city.lower())
    if not c:
        return ""
    letter = c[-1]
    if letter in SKIPPABLE_LAST_LETTERS and len(c) > 1:
        letter = c[-2]
    return LETTER_ALIASES.get(letter, letter)


def first_letter(city: str) -> str:
    """First letter with alias mapping."""
    c = city.strip().lower()
    if not c:
        return ""
    return LETTER_ALIASES.get(c[0], c[0])


def is_valid_city_input(text: str) -> bool:
    """Basic shape check."""
    return bool(CITY_RE.match(text.strip()))


def is_valid_city_name(text: str) -> bool:
    """Проверка имени города (буквы/дефисы, 2–50 символов)."""
    cleaned = text.strip()
    return bool(CITY_RE.match(cleaned)) and len(cleaned) >= 2


def parse_coordinates(text: str) -> tuple[float, float] | None:
    """Parse '55.75, 37.61' → (lat, lon) or None."""
    m = COORD_RE.match(text.strip())
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon