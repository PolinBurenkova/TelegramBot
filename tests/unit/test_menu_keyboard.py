"""Юнит-тесты меню: reply-клавиатура и её обработчики.

Проверяется то, из-за чего меню «не выпадало» на мобильном: клавиатура должна
быть persistent (не сворачиваться), а каждый её текст — иметь хендлер.
"""
from __future__ import annotations

from app.handlers.menu import CB_BACK, router as menu_router
from app.keyboards import main_menu_kb
from app.keyboards.common import back_kb
from app.keyboards.main_menu import MAIN_MENU_TEXTS


def _button_texts(markup) -> list[str]:
    return [button.text for row in markup.keyboard for button in row]


def test_reply_keyboard_is_persistent_and_resized() -> None:
    markup = main_menu_kb()

    assert markup.resize_keyboard is True
    assert markup.is_persistent is True
    assert markup.input_field_placeholder


def test_all_menu_buttons_are_unique_and_declared() -> None:
    texts = _button_texts(main_menu_kb())

    assert len(texts) == len(MAIN_MENU_TEXTS)
    assert set(texts) == MAIN_MENU_TEXTS
    assert len(set(texts)) == len(texts)


def test_every_menu_button_has_message_handler() -> None:
    names = {
        handler.callback.__name__
        for handler in menu_router.message.handlers
        if hasattr(handler.callback, "__name__")
    }

    expected = {
        "cmd_menu",
        "menu_play",
        "menu_geo",
        "menu_profile",
        "menu_achievements",
        "menu_leaderboard",
        "menu_settings",
        "menu_help",
    }
    assert expected <= names


def test_menu_handles_back_and_main_callbacks() -> None:
    names = {
        handler.callback.__name__
        for handler in menu_router.callback_query.handlers
        if hasattr(handler.callback, "__name__")
    }

    assert {"back_to_menu", "back_button"} <= names


def test_back_button_payload_is_handled_by_menu() -> None:
    payload = back_kb().inline_keyboard[0][0].callback_data

    assert payload == CB_BACK
