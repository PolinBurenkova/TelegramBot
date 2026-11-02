"""Profile schemas."""
from __future__ import annotations

from datetime import datetime

from app.schemas.common import BaseSchema


class ProfileOut(BaseSchema):
    """Raw profile data."""

    id: int
    user_id: int
    level: int
    xp: int
    total_games: int
    total_wins: int
    cities_score: int
    geo_score: int
    streak_days: int
    last_played_at: datetime | None = None


class ProfileView(BaseSchema):
    """Rendered profile with computed fields."""

    username: str
    level: int
    xp: int
    xp_in_level: int
    xp_to_next: int
    progress_bar: str
    total_games: int
    total_wins: int
    winrate: float
    total_score: int
    streak_days: int