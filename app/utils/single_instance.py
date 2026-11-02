"""Защита от второго экземпляра бота на одной машине.

Второй `run.py` с тем же токеном начинает конкурировать за `getUpdates` и
Telegram отвечает `TelegramConflictError` — но aiogram ретраит его бесконечно,
поэтому в логе появляется бесконечная серия ошибок, а бот не работает.

Здесь используется блокировка файла средствами ОС: она снимается автоматически
при завершении процесса, поэтому «вечных» локов после падения не остаётся.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import TracebackType

#: Блокируемый байт вынесен за пределы записываемых данных: в Windows
#: заблокированный диапазон нельзя прочитать другим хендлом, поэтому PID
#: пишется в начало файла, а лочится пустая область.
_LOCK_OFFSET = 1024


class SingleInstance:
    """Эксклюзивная блокировка файла (OS-лок, без сетевых вызовов)."""

    def __init__(self, path: Path | str = "data/bot.lock") -> None:
        self.path = Path(path)
        self._handle: object | None = None
        self._fd: int | None = None

    @property
    def acquired(self) -> bool:
        """Захвачена ли блокировка этим объектом."""
        return self._handle is not None

    def acquire(self) -> bool:
        """Попытаться занять лок. False — лок уже держит другой процесс."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+", encoding="utf-8")
        try:
            if sys.platform == "win32":
                import msvcrt

                handle.seek(_LOCK_OFFSET)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False

        try:
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n")
            handle.flush()
        except OSError:
            pass

        self._handle = handle
        return True

    def release(self) -> None:
        """Снять блокировку (идемпотентно)."""
        handle = self._handle
        if handle is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                handle.seek(_LOCK_OFFSET)  # type: ignore[attr-defined]
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
        except OSError:
            pass
        finally:
            try:
                handle.close()  # type: ignore[attr-defined]
            finally:
                self._handle = None

    def __enter__(self) -> "SingleInstance":
        if not self.acquire():
            raise RuntimeError(f"Бот уже запущен (лок {self.path})")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
