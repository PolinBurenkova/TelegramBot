"""Интеграционные тесты сервиса настроек пользователя.

Проверяют маппинг полей ``User`` в ``SettingsSchema`` и правила частичного
обновления без сети и без Telegram. Используется сессия из ``db_session``.
"""
from __future__ import annotations

import pytest

from app.schemas.settings import SettingsSchema, SettingsUpdate
from app.services.settings_service import SettingsService

pytestmark = pytest.mark.integration


async def test_get_returns_defaults_for_fresh_user(db_session, sample_user):
    service = SettingsService(db_session)

    result = await service.get(sample_user)

    assert isinstance(result, SettingsSchema)
    assert result.locale == "ru"
    assert result.notify is True
    assert result.difficulty == "easy"
    assert result.timezone == "UTC"


async def test_get_reflects_user_fields(db_session, sample_user):
    sample_user.locale = "en"
    sample_user.notify = False
    sample_user.difficulty = "hard"
    await db_session.flush()
    service = SettingsService(db_session)

    result = await service.get(sample_user)

    assert result.locale == "en"
    assert result.notify is False
    assert result.difficulty == "hard"


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
async def test_set_difficulty_accepts_known_values(db_session, sample_user, difficulty):
    service = SettingsService(db_session)

    await service.set_difficulty(sample_user, difficulty)

    assert sample_user.difficulty == difficulty


@pytest.mark.parametrize("invalid", ["", "HARD", "nightmare"])
async def test_set_difficulty_falls_back_to_easy(db_session, sample_user, invalid):
    service = SettingsService(db_session)

    await service.set_difficulty(sample_user, invalid)

    assert sample_user.difficulty == "easy"


async def test_update_applies_locale_and_notify(db_session, sample_user):
    service = SettingsService(db_session)

    result = await service.update(
        sample_user, SettingsUpdate(locale="en", notify=False)
    )

    assert sample_user.locale == "en"
    assert sample_user.notify is False
    assert result.locale == "en"
    assert result.notify is False


async def test_update_keeps_fields_when_none(db_session, sample_user):
    service = SettingsService(db_session)

    result = await service.update(sample_user, SettingsUpdate())

    assert sample_user.locale == "ru"
    assert sample_user.notify is True
    assert result.locale == "ru"
    assert result.notify is True


async def test_update_ignores_difficulty_and_timezone(db_session, sample_user):
    service = SettingsService(db_session)

    result = await service.update(
        sample_user,
        SettingsUpdate(difficulty="hard", timezone="Europe/Moscow"),
    )

    assert sample_user.difficulty == "easy"
    assert result.difficulty == "easy"
    assert result.timezone == "UTC"


async def test_settings_schema_defaults():
    schema = SettingsSchema()

    assert schema.locale == "ru"
    assert schema.notify is True
    assert schema.difficulty == "easy"
    assert schema.timezone == "UTC"
