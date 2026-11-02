"""Ежедневное задание: выбор города на дату, проверка ответа."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import WIN_BONUS
from app.models.city import City
from app.models.daily_challenge import DailyChallenge
from app.repositories.city_repo import CityRepo
from app.utils.validators import normalize_city


class DailyChallengeService:
    """Одно задание в сутки: угадать город по подсказке."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cities = CityRepo(session)

    @staticmethod
    def _today() -> date:
        return datetime.now(timezone.utc).date()

    async def get_by_date(self, day: date | None = None) -> DailyChallenge | None:
        """Задание на дату (по умолчанию — сегодня)."""
        target = day or self._today()
        result = await self.session.execute(
            select(DailyChallenge).where(DailyChallenge.challenge_date == target)
        )
        return result.scalar_one_or_none()

    async def get_or_create_today(self) -> DailyChallenge | None:
        """Вернуть задание на сегодня, создав его при необходимости.

        Город выбирается один раз и сохраняется в БД, поэтому повторные
        вызовы в течение дня дают одно и то же задание. Если справочник
        городов пуст — возвращается None (сиды не загружены).
        """
        existing = await self.get_by_date()
        if existing is not None:
            return existing

        # Ограничений по населению нет — подходит любой город справочника.
        city = await self.cities.random()
        if city is None:
            return None

        challenge = DailyChallenge(
            challenge_date=self._today(),
            city_name=city.name,
            hint=self._make_hint(city),
            reward_score=WIN_BONUS,
        )
        self.session.add(challenge)
        await self.session.flush()
        return challenge

    @staticmethod
    def _make_hint(city: City) -> str:
        """Подсказка: регион/страна и первая буква, без названия города."""
        parts = [f"Первая буква: {city.name[:1].upper()}"]
        if city.country_name:
            parts.append(f"Страна: {city.country_name}")
        elif city.country_code:
            parts.append(f"Страна: {city.country_code}")
        if city.region:
            parts.append(f"Регион: {city.region}")
        return " · ".join(parts)[:255]

    async def submit(self, user_id: int, answer: str) -> dict[str, object]:
        """Проверить ответ на сегодняшнее задание.

        Возвращает словарь с результатом; начисление очков выполняет
        вызывающий код (сервис не трогает профиль).
        """
        challenge = await self.get_or_create_today()
        if challenge is None:
            return {
                "ok": False,
                "reason": "no_cities",
                "correct": False,
                "reward": 0,
            }
        correct = normalize_city(answer) == normalize_city(challenge.city_name)
        return {
            "ok": True,
            "correct": correct,
            "reward": challenge.reward_score if correct else 0,
            "city_name": challenge.city_name if correct else None,
            "challenge_date": challenge.challenge_date.isoformat(),
            "user_id": user_id,
        }
