"""Тесты разворачивания `Update` в middleware (app/bot/middlewares/base.py).

`dp.update.outer_middleware` получает `Update`, а не `Message`, поэтому
`event.from_user` там всегда `None` — из-за этого `UserContextMiddleware`
молча не выставлял `data["user"]`, и хендлеры с параметром `user` падали.
"""
from __future__ import annotations

from aiogram.types import Update

from app.bot.middlewares.base import event_user, unwrap_event

USER_PAYLOAD = {
    "id": 1_000_000_002,
    "is_bot": False,
    "first_name": "Тест",
    "username": "tester",
}

MESSAGE_PAYLOAD = {
    "message_id": 10,
    "date": 1_700_000_000,
    "chat": {"id": 1_000_000_002, "type": "private"},
    "from": USER_PAYLOAD,
    "text": "Москва",
}


def _update_message() -> Update:
    return Update.model_validate({"update_id": 1, "message": MESSAGE_PAYLOAD})


def _update_callback() -> Update:
    return Update.model_validate(
        {
            "update_id": 2,
            "callback_query": {
                "id": "cb-1",
                "chat_instance": "ci-1",
                "from": USER_PAYLOAD,
                "data": "menu:main",
                "message": dict(MESSAGE_PAYLOAD, text=None),
            },
        }
    )


def test_unwrap_update_returns_message() -> None:
    update = _update_message()

    assert unwrap_event(update) is update.message


def test_unwrap_update_returns_callback_query() -> None:
    update = _update_callback()

    assert unwrap_event(update) is update.callback_query


def test_unwrap_plain_message_is_noop() -> None:
    message = _update_message().message

    assert unwrap_event(message) is message


def test_event_user_extracts_from_user_of_update() -> None:
    user = event_user(_update_message())

    assert user is not None
    assert user.id == USER_PAYLOAD["id"]


def test_event_user_extracts_from_callback_query() -> None:
    user = event_user(_update_callback())

    assert user is not None
    assert user.id == USER_PAYLOAD["id"]


def test_event_user_is_none_for_unsupported_event() -> None:
    update = Update.model_validate({"update_id": 3})

    assert event_user(update) is None
