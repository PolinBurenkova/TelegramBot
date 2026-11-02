"""Декораторы: замер времени выполнения и логирование вызовов."""
from __future__ import annotations

import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


def measure_time(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Log execution time."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        t0 = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            dt = (time.perf_counter() - t0) * 1000
            logging.getLogger(func.__module__).debug("%s took %.1fms", func.__name__, dt)

    return wrapper


def log_calls(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Log call."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        logging.getLogger(func.__module__).debug("call %s", func.__name__)
        return await func(*args, **kwargs)

    return wrapper