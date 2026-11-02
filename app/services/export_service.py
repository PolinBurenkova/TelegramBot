"""Экспорт прогресса пользователя: словарь, JSON, CSV."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.profile import Profile
from app.models.user import User
from app.repositories.achievement_repo import UserAchievementRepo
from app.repositories.game_repo import GameRepo
from app.repositories.profile_repo import ProfileRepo
from app.repositories.user_repo import UserRepo

CSV_COLUMNS: tuple[str, ...] = (
    "game_id",
    "started_at",
    "finished_at",
    "game_type",
    "difficulty",
    "status",
    "moves_count",
    "score",
    "won",
)


class ExportService:
    """Собирает данные пользователя без записи файлов на диск."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepo(session)
        self.profiles = ProfileRepo(session)
        self.games = GameRepo(session)
        self.user_achievements = UserAchievementRepo(session)

    async def _user(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def export_user(self, user_id: int) -> dict[str, Any] | None:
        """Полный снимок: пользователь, профиль, партии, достижения."""
        user = await self._user(user_id)
        if user is None:
            return None
        profile: Profile | None = await self.profiles.get_by_user(user_id)
        games: list[Game] = await self.games.list_by_user(user_id, page=0, size=500)
        unlocked = await self.user_achievements.list_by_user(user_id)
        return {
            "user": {
                "id": user.id,
                "tg_id": user.tg_id,
                "username": user.username,
                "locale": user.locale,
                "created_at": user.created_at.isoformat()
                if getattr(user, "created_at", None)
                else None,
            },
            "profile": {
                "level": getattr(profile, "level", None),
                "xp": getattr(profile, "xp", None),
                "cities_score": getattr(profile, "cities_score", None),
                "geo_score": getattr(profile, "geo_score", None),
                "games_played": getattr(profile, "games_played", None),
                "games_won": getattr(profile, "games_won", None),
            }
            if profile
            else None,
            "games": [
                {
                    "id": str(game.id),
                    "game_type": getattr(game.game_type, "value", game.game_type),
                    "status": getattr(game.status, "value", game.status),
                    "difficulty": game.difficulty,
                    "moves_count": game.moves_count,
                    "score": game.score,
                    "won": game.won,
                    "started_at": game.started_at.isoformat()
                    if game.started_at
                    else None,
                    "finished_at": game.finished_at.isoformat()
                    if game.finished_at
                    else None,
                }
                for game in games
            ],
            "achievements": [
                {
                    "achievement_id": item.achievement_id,
                    "unlocked_at": item.unlocked_at.isoformat()
                    if getattr(item, "unlocked_at", None)
                    else None,
                }
                for item in unlocked
            ],
        }

    async def export_json(self, user_id: int) -> str:
        """JSON-строка с данными пользователя (пустой объект, если нет юзера)."""
        data = await self.export_user(user_id)
        return json.dumps(data if data is not None else {}, ensure_ascii=False, indent=2)

    async def export_csv(self, user_id: int) -> str:
        """CSV с партиями пользователя (шапка есть даже без партий)."""
        games: list[Game] = await self.games.list_by_user(user_id, page=0, size=500)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for game in games:
            writer.writerow(
                {
                    "game_id": str(game.id),
                    "started_at": game.started_at.isoformat()
                    if game.started_at
                    else "",
                    "finished_at": game.finished_at.isoformat()
                    if game.finished_at
                    else "",
                    "game_type": getattr(game.game_type, "value", game.game_type),
                    "difficulty": game.difficulty,
                    "status": getattr(game.status, "value", game.status),
                    "moves_count": game.moves_count,
                    "score": game.score,
                    "won": int(bool(game.won)),
                }
            )
        return buffer.getvalue()
