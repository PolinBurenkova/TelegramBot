"""Тесты меню команд бота (`app/bot/bot_factory.BOT_COMMANDS`).

Список команд регистрируется через Bot API (`set_my_commands`), поэтому
мобильный и десктопный клиенты показывают одинаковое меню «/». Здесь
проверяется формат команд и то, что каждая из них реально обрабатывается
хендлером.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.bot.bot_factory import BOT_COMMANDS, DESCRIPTION, SHORT_DESCRIPTION

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLERS_DIR = REPO_ROOT / "app" / "handlers"

COMMAND_RE = re.compile(r"^[a-z0-9_]{1,32}$")
HANDLED_RE = re.compile(r'Command\("([a-z0-9_]+)"\)')


def _handled_commands() -> set[str]:
    """Команды, на которые есть фильтр Command(...) в app/handlers."""
    handled: set[str] = set()
    for path in HANDLERS_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        handled.update(HANDLED_RE.findall(text))
        if "CommandStart()" in text:
            handled.add("start")
    return handled


def test_commands_are_unique_and_valid() -> None:
    names = [name for name, _ in BOT_COMMANDS]

    assert len(names) == len(set(names))
    for name in names:
        assert COMMAND_RE.match(name), f"некорректное имя команды: {name}"


def test_descriptions_fit_telegram_limits() -> None:
    for name, text in BOT_COMMANDS:
        assert 1 <= len(text) <= 256, f"{name}: длина описания {len(text)}"


def test_every_advertised_command_has_handler() -> None:
    advertised = {name for name, _ in BOT_COMMANDS}
    handled = _handled_commands()

    missing = sorted(advertised - handled)
    assert not missing, f"нет хендлера для команд: {missing}"


def test_menu_commands_present() -> None:
    advertised = {name for name, _ in BOT_COMMANDS}

    assert {"start", "menu", "play", "geo", "help"} <= advertised


def test_bot_descriptions_non_empty() -> None:
    assert SHORT_DESCRIPTION.strip()
    assert 0 < len(SHORT_DESCRIPTION) <= 120
    assert 0 < len(DESCRIPTION) <= 512
