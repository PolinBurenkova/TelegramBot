"""Pagination helper."""
from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


def paginate(items: list[T], page: int, size: int) -> tuple[list[T], int, bool, bool]:
    """Return (page_items, total_pages, has_prev, has_next)."""
    total = len(items)
    pages = max(1, (total + size - 1) // size)
    page = max(0, min(page, pages - 1))
    start = page * size
    end = start + size
    return items[start:end], pages, page > 0, page + 1 < pages
    return max(1, (len(items) + per_page - 1) // per_page)