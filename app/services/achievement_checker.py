"""Условия достижений."""

from app.constants import (
    ACHIEVEMENT_FIRST_CITY,
    ACHIEVEMENT_GEO_MASTER,
    ACHIEVEMENT_LEGEND,
    ACHIEVEMENT_POLYGLOT,
    ACHIEVEMENT_TRAVELER,
    ACHIEVEMENT_WEATHER_WIZARD,
    ACHIEVEMENTS_REQUIREMENTS,
)


def check_achievements(
    *,
    cities_used: int,
    countries_visited: int,
    xp: int,
    geo_avg_score: float,
    weather_requests: int = 0,
) -> list[str]:
    """Возвращает коды достижений, которые заслужил пользователь."""
    unlocked: list[str] = []
    if cities_used >= ACHIEVEMENTS_REQUIREMENTS[ACHIEVEMENT_FIRST_CITY]:
        unlocked.append(ACHIEVEMENT_FIRST_CITY)
    if cities_used >= ACHIEVEMENTS_REQUIREMENTS[ACHIEVEMENT_POLYGLOT]:
        unlocked.append(ACHIEVEMENT_POLYGLOT)
    if countries_visited >= ACHIEVEMENTS_REQUIREMENTS[ACHIEVEMENT_TRAVELER]:
        unlocked.append(ACHIEVEMENT_TRAVELER)
    if xp >= ACHIEVEMENTS_REQUIREMENTS[ACHIEVEMENT_LEGEND]:
        unlocked.append(ACHIEVEMENT_LEGEND)
    if geo_avg_score >= ACHIEVEMENTS_REQUIREMENTS[ACHIEVEMENT_GEO_MASTER]:
        unlocked.append(ACHIEVEMENT_GEO_MASTER)
    if weather_requests >= ACHIEVEMENTS_REQUIREMENTS[ACHIEVEMENT_WEATHER_WIZARD]:
        unlocked.append(ACHIEVEMENT_WEATHER_WIZARD)
    return unlocked