"""Юнит-тесты лока одного экземпляра бота (`app/utils/single_instance.py`).

Лок защищает от второго `run.py`: иначе два процесса забирают `getUpdates`,
Telegram отвечает `TelegramConflictError`, и бот не работает.
"""
from __future__ import annotations

from app.utils.single_instance import SingleInstance


def test_acquire_creates_file_and_blocks_second_instance(tmp_path) -> None:
    path = tmp_path / "bot.lock"
    first = SingleInstance(path)

    assert first.acquire() is True
    assert path.exists()

    second = SingleInstance(path)
    try:
        assert second.acquire() is False
    finally:
        first.release()

    # После освобождения лок можно занять снова
    assert second.acquire() is True
    second.release()


def test_release_is_idempotent(tmp_path) -> None:
    lock = SingleInstance(tmp_path / "bot.lock")

    assert lock.acquire() is True
    lock.release()
    lock.release()  # повторный вызов не бросает исключение

    assert lock.acquired is False


def test_context_manager_releases_lock(tmp_path) -> None:
    path = tmp_path / "bot.lock"

    with SingleInstance(path) as lock:
        assert lock.acquired is True

    assert lock.acquired is False
    again = SingleInstance(path)
    assert again.acquire() is True
    again.release()
