# tests/fixtures/users.py
"""Фабрики тестовых данных пользователей.

Никаких обращений к сети и БД: функции только собирают данные/объекты модели.
Поля берутся из реальной модели `app.models.user.User` (поле tg_id, не telegram_id).
"""

from __future__ import annotations

from typing import Any

from app.models import User

DEFAULT_USER_TG_ID = 1_000_000_002


def user_data(**overrides: Any) -> dict[str, Any]:
    """Данные пользователя для передачи в `User(**user_data())`."""
    data: dict[str, Any] = {
        "tg_id": DEFAULT_USER_TG_ID,
        "username": "test_user",
        "first_name": "Тест",
        "language": "ru",
        "locale": "ru",
        "total_score": 0,
        "level": 0,
        "difficulty": "easy",
        "show_weather": True,
        "show_photo": True,
        "notify": True,
        "is_banned": False,
    }
    data.update(overrides)
    return data


def make_user(**overrides: Any) -> User:
    """Экземпляр `User` (не сохранённый в БД)."""
    return User(**user_data(**overrides))


__all__ = ["DEFAULT_USER_TG_ID", "make_user", "user_data"]
