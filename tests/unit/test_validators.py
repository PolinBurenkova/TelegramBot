# tests/unit/test_validators.py
"""Валидаторы имён городов и координат — чистые функции без сети и БД."""

import pytest

from app.utils.validators import (
    first_letter,
    is_valid_city_name,
    last_letter,
    normalize_city,
    parse_coordinates,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Москва ", "москва"),
        ("Королёв", "королев"),
        ("Нижний   Новгород", "нижний новгород"),
        ("Санкт-Петербург", "санкт-петербург"),
    ],
)
def test_normalize_city(raw: str, expected: str) -> None:
    assert normalize_city(raw) == expected


@pytest.mark.parametrize(
    ("city", "expected"),
    [
        ("Астрахань", "н"),
        ("Москва", "а"),
        ("Сочи", "и"),
        ("Йошкар-Ола", "а"),
        # «й» больше не отбрасывается — следующий город должен начинаться на «й»
        ("Волжский", "й"),
        ("Краснознаменский", "й"),
        ("Тверь", "т"),
    ],
)
def test_last_letter_rules(city: str, expected: str) -> None:
    assert last_letter(city) == expected


def test_last_letter_handles_empty_input() -> None:
    assert last_letter("") == ""


def test_first_letter_alias() -> None:
    assert first_letter("Ёлка") == "е"
    assert first_letter("") == ""


@pytest.mark.parametrize("text", ["Москва", "Санкт-Петербург", "Ростов-на-Дону"])
def test_valid_city_names(text: str) -> None:
    assert is_valid_city_name(text)


@pytest.mark.parametrize("text", ["", "М", "Москва1", "??", "город 123"])
def test_invalid_city_names(text: str) -> None:
    assert not is_valid_city_name(text)


def test_parse_coordinates_ok() -> None:
    assert parse_coordinates("55.75, 37.61") == (55.75, 37.61)
    assert parse_coordinates("-33.9;151.2") == (-33.9, 151.2)


@pytest.mark.parametrize("text", ["", "abc", "95.0, 10.0", "10.0, 200.0"])
def test_parse_coordinates_rejects_bad_input(text: str) -> None:
    assert parse_coordinates(text) is None
