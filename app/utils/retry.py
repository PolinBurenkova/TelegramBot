"""Retry-обёртки на tenacity."""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.constants import RETRY_ATTEMPTS, RETRY_MAX_WAIT, RETRY_MIN_WAIT

T = TypeVar("T")

RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadTimeout,
)


def build_retry() -> AsyncRetrying:
    """Собирает AsyncRetrying с настройками из констант."""
    return AsyncRetrying(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
    )


retry_async = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)


async def call_with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Вызывает async-функцию с retry."""
    async for attempt in build_retry():
        with attempt:
            return await func(*args, **kwargs)
    raise RetryError("retry exhausted")