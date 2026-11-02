"""Level math wrapper."""
from __future__ import annotations

from app.constants import MAX_LEVEL
from app.utils.xp import level_from_xp, xp_for_level


class LevelService:
    """Level calculations."""

    @staticmethod
    def level_from_xp(xp: int) -> tuple[int, int, int]:
        level, cur, need = level_from_xp(xp)
        return min(level, MAX_LEVEL), cur, need

    @staticmethod
    def xp_for_level(level: int) -> int:
        return xp_for_level(level)