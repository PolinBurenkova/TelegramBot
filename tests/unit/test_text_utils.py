# tests/unit/test_text_utils.py
"""Юнит-тесты текстовых хелперов (`app/utils/text.py`).

Имя файла оставлено по контракту задачи (test_text_utils.py),
хотя модуль приложения называется `app/utils/text.py`.
"""

from __future__ import annotations

import pytest

from app.utils.text import escape_html, pluralize, truncate

GAME_FORMS = ("игра", "игры", "игр")


def test_truncate_short_text_is_unchanged() -> None:
    assert truncate("Москва", limit=20) == "Москва"


def test_truncate_long_text_fits_limit_with_suffix() -> None:
    result = truncate("0123456789", limit=5)

    assert result == "0123…"
    assert len(result) == 5
    assert result.endswith("…")


def test_truncate_custom_suffix() -> None:
    assert truncate("0123456789", limit=6, suffix="!!") == "0123!!"


def test_truncate_exact_length_unchanged() -> None:
    assert truncate("01234", limit=5) == "01234"


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, "игр"),
        (1, "игра"),
        (2, "игры"),
        (4, "игры"),
        (5, "игр"),
        (11, "игр"),
        (12, "игр"),
        (14, "игр"),
        (21, "игра"),
        (22, "игры"),
        (25, "игр"),
        (100, "игр"),
        (101, "игра"),
        (111, "игр"),
    ],
    ids=["0", "1", "2", "4", "5", "11", "12", "14", "21", "22", "25", "100", "101", "111"],
)
def test_pluralize(n: int, expected: str) -> None:
    assert pluralize(n, GAME_FORMS) == expected


def test_escape_html_escapes_special_chars() -> None:
    assert escape_html("<b>Москва & Ко</b>") == "&lt;b&gt;Москва &amp; Ко&lt;/b&gt;"


def test_escape_html_plain_text_unchanged() -> None:
    assert escape_html("Москва") == "Москва"


def test_escape_html_escapes_ampersand_first() -> None:
    # Пользовательский ввод вида "&amp;" экранируется один раз:
    # получаем литерал "&amp;amp;" — так и должно быть для безопасного HTML.
    assert escape_html("&amp;") == "&amp;amp;"
