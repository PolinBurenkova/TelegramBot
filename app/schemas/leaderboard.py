"""Leaderboard schemas."""
from __future__ import annotations

from app.schemas.common import BaseSchema


class LeaderboardEntry(BaseSchema):
    """One row in leaderboard."""

    rank: int
    username: str
    level: int
    score: int


class LeaderboardPage(BaseSchema):
    """Leaderboard page."""

    entries: list[LeaderboardEntry]
    total: int
    page: int
    pages: int