"""User lifecycle, XP, profile view, reset."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.profile_repo import ProfileRepo
from app.repositories.user_repo import UserRepo
from app.repositories.user_used_city_repo import UserUsedCityRepo
from app.schemas.profile import ProfileView
from app.utils.xp import level_from_xp, progress_bar


class UserService:
    """User + profile orchestration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepo(session)
        self.profiles = ProfileRepo(session)
        self.used_cities = UserUsedCityRepo(session)

    async def get_or_create(self, tg_id: int, username: str | None) -> User:
        """Fetch or create user + profile."""
        user = await self.users.get_by_tg_id(tg_id)
        if user:
            if username and user.username != username:
                user.username = username
            await self.users.update_last_seen(user)
            return user
        return await self.users.create_with_profile(tg_id, username)

    async def get_profile_view(self, user: User) -> ProfileView:
        """Computed profile view for UI."""
        p = user.profile
        level, in_lvl, need = level_from_xp(p.xp)
        winrate = (p.total_wins / p.total_games * 100) if p.total_games else 0.0
        return ProfileView(
            username=user.username or str(user.tg_id),
            level=level,
            xp=p.xp,
            xp_in_level=in_lvl,
            xp_to_next=need,
            progress_bar=progress_bar(in_lvl, need),
            total_games=p.total_games,
            total_wins=p.total_wins,
            winrate=winrate,
            total_score=p.cities_score + p.geo_score,
            streak_days=p.streak_days,
        )

    async def reset_progress(self, user: User) -> None:
        """Wipe progress."""
        await self.profiles.reset(user.profile)
        await self.used_cities.clear_for_user(user.id)

    async def update_locale(self, user: User, locale: str) -> None:
        await self.users.update_locale(user, locale)

    async def toggle_notify(self, user: User) -> bool:
        new_val = not user.notify
        await self.users.set_notify(user, new_val)
        return new_val