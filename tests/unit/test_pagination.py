# tests/unit/test_pagination.py
"""Юнит-тесты пагинации: утилита и инлайн-клавиатура.

`paginate` возвращает кортеж (items, pages, has_prev, has_next);
`app.keyboards.pagination` строит клавиатуру «◀️ N/M ▶️» с теми же
правилами границ.
"""

from __future__ import annotations

import pytest

from app.utils.pagination import paginate

ITEMS = list(range(10))


@pytest.mark.parametrize(
    ("page", "size", "expected_items", "expected_pages", "has_prev", "has_next"),
    [
        (0, 3, [0, 1, 2], 4, False, True),
        (1, 3, [3, 4, 5], 4, True, True),
        (3, 3, [9], 4, True, False),
        (99, 3, [9], 4, True, False),
        (-5, 3, [0, 1, 2], 4, False, True),
        (0, 10, ITEMS, 1, False, False),
        (0, 100, ITEMS, 1, False, False),
    ],
    ids=[
        "first-page",
        "middle-page",
        "last-page",
        "page-clamped-high",
        "page-clamped-low",
        "single-page",
        "size-larger-than-total",
    ],
)
def test_paginate(
    page: int,
    size: int,
    expected_items: list[int],
    expected_pages: int,
    has_prev: bool,
    has_next: bool,
) -> None:
    items, pages, prev, nxt = paginate(ITEMS, page, size)

    assert items == expected_items
    assert pages == expected_pages
    assert prev is has_prev
    assert nxt is has_next


@pytest.mark.parametrize(
    ("count", "size", "expected_pages"),
    [(0, 5, 1), (1, 5, 1), (5, 5, 1), (6, 5, 2), (9, 3, 3), (10, 3, 4)],
    ids=["empty", "one", "exact", "plus-one", "exact-3", "plus-one-4"],
)
def test_paginate_total_pages(count: int, size: int, expected_pages: int) -> None:
    _, pages, _, _ = paginate(list(range(count)), 0, size)

    assert pages == expected_pages


def test_paginate_empty_list() -> None:
    items, pages, has_prev, has_next = paginate([], 0, 10)

    assert items == []
    assert pages == 1
    assert has_prev is False
    assert has_next is False


# ─── инлайн-клавиатура пагинации (app/keyboards/pagination.py) ──────────────


@pytest.mark.parametrize(
    ("page", "total", "expected"),
    [
        (0, 3, 0),
        (2, 3, 2),
        (5, 3, 2),
        (-4, 3, 0),
        (1, 0, 0),
    ],
    ids=["first", "last", "too-high", "negative", "zero-pages"],
)
def test_clamp_page(page: int, total: int, expected: int) -> None:
    from app.keyboards.pagination import clamp_page

    assert clamp_page(page, total) == expected


def _callbacks(markup) -> list[list[str]]:
    return [
        [button.callback_data for button in row] for row in markup.inline_keyboard
    ]


def test_pagination_kb_first_page_has_only_next() -> None:
    markup = pagination_kb("ach:page", 0, 3)

    assert _callbacks(markup) == [["noop", "ach:page:1"]]


def test_pagination_kb_last_page_has_only_prev() -> None:
    markup = pagination_kb("ach:page", 2, 3)

    assert _callbacks(markup) == [["ach:page:1", "noop"]]


def test_pagination_kb_single_page_and_back_button() -> None:
    markup = pagination_kb("ach:page", 0, 1, back_callback="menu:main")

    assert _callbacks(markup) == [["noop"], ["menu:main"]]


def test_pagination_kb_clamps_out_of_range_page() -> None:
    markup = pagination_kb("ach:page", 99, 2)

    assert _callbacks(markup) == [["ach:page:0", "noop"]]

