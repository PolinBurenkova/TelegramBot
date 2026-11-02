"""Корневой роутер: собирает все хендлеры в порядке приоритета."""
from __future__ import annotations

from aiogram import Router

from app.handlers.achievements import router as achievements_router
from app.handlers.admin import router as admin_router
from app.handlers.cancel import router as cancel_router
from app.handlers.cities_game import router as cities_game_router
from app.handlers.errors import router as errors_router
from app.handlers.fallback import router as fallback_router
from app.handlers.geoguessr import router as geoguessr_router
from app.handlers.help import router as help_router
from app.handlers.leaderboard import router as leaderboard_router
from app.handlers.menu import router as menu_router
from app.handlers.profile import router as profile_router
from app.handlers.reset_progress import router as reset_progress_router
from app.handlers.settings import router as settings_router
from app.handlers.start import router as start_router
from app.handlers.stats import router as stats_router

root_router = Router(name="root")

# Порядок важен: более специфичные роутеры — раньше; errors и fallback
# (catch-all) — последними.
_ORDERED = (
    start_router,
    menu_router,
    cities_game_router,
    geoguessr_router,
    settings_router,
    profile_router,
    leaderboard_router,
    stats_router,
    achievements_router,
    admin_router,
    reset_progress_router,
    help_router,
    cancel_router,
)

for _sub in _ORDERED:
    root_router.include_router(_sub)

root_router.include_router(errors_router)
root_router.include_router(fallback_router)
