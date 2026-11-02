"""Тесты `run.shutdown` — корректное закрытие ресурсов при любом выходе.

Именно отсутствие закрытия сессии давало в консоли `Unclosed connector`
и `RuntimeError: Event loop is closed` после ошибки запуска (например, 401).
"""
from __future__ import annotations

from typing import Any

from run import shutdown


class _FakeSession:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.closed = False

    async def close(self) -> None:
        self.closed = True
        if self.fail:
            raise RuntimeError("session close failed")


class _FakeStorage:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.closed = False

    async def close(self) -> None:
        self.closed = True
        if self.fail:
            raise RuntimeError("storage close failed")


class _FakeBot:
    def __init__(self, fail: bool = False) -> None:
        self.session = _FakeSession(fail=fail)


class _FakeDp:
    def __init__(self, fail: bool = False) -> None:
        self.storage = _FakeStorage(fail=fail)


class _FakeLock:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.released = False

    def release(self) -> None:
        self.released = True
        if self.fail:
            raise RuntimeError("lock release failed")


async def test_shutdown_closes_session_storage_and_lock() -> None:
    bot = _FakeBot()
    dp = _FakeDp()
    lock = _FakeLock()

    await shutdown(bot, dp, lock)  # type: ignore[arg-type]

    assert bot.session.closed
    assert dp.storage.closed
    assert lock.released


async def test_shutdown_survives_failing_resources() -> None:
    bot = _FakeBot(fail=True)
    dp = _FakeDp(fail=True)
    lock = _FakeLock(fail=True)

    await shutdown(bot, dp, lock)  # type: ignore[arg-type]

    assert bot.session.closed
    assert dp.storage.closed
    assert lock.released


async def test_shutdown_without_lock() -> None:
    bot = _FakeBot()
    dp: Any = _FakeDp()

    await shutdown(bot, dp, None)  # type: ignore[arg-type]

    assert bot.session.closed
