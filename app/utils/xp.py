"""XP / level math."""
from __future__ import annotations

from app.constants import XP_LEVEL_BASE, XP_LEVEL_EXPONENT


def xp_for_level(level: int) -> int:
    """Total XP needed to reach given level."""
    if level <= 1:
        return 0
    return int(XP_LEVEL_BASE * ((level - 1) ** XP_LEVEL_EXPONENT))


def level_from_xp(xp: int) -> tuple[int, int, int]:
    """Return (level, xp_in_level, xp_for_next_level)."""
    level = 1
    while xp_for_level(level + 1) <= xp and level < 1000:
        level += 1
    cur = xp_for_level(level)
    nxt = xp_for_level(level + 1)
    return level, xp - cur, nxt - cur


def progress_bar(current: int, total: int, width: int = 10) -> str:
    """Text progress bar."""
    if total <= 0:
        return "▱" * width
    filled = min(width, round(current / total * width))
    return "▰" * filled + "▱" * (width - filled)