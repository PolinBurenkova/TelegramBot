"""Text helpers."""
from __future__ import annotations


def truncate(text: str, limit: int = 200, suffix: str = "…") -> str:
    """Truncate text."""
    if len(text) <= limit:
        return text
    return text[: limit - len(suffix)] + suffix


def pluralize(n: int, forms: tuple[str, str, str]) -> str:
    """Russian plural forms: (1 игра, 2 игры, 5 игр)."""
    n10, n100 = n % 10, n % 100
    if 11 <= n100 <= 19:
        return forms[2]
    if n10 == 1:
        return forms[0]
    if 2 <= n10 <= 4:
        return forms[1]
    return forms[2]


def escape_html(text: str) -> str:
    """Escape < > &."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )