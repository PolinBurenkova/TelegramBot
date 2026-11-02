"""Simple token-bucket rate limiter (in-memory)."""
from __future__ import annotations

import time


class RateLimiter:
    """Allow `rate` calls per second."""

    def __init__(self, rate: float, burst: int = 1) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens: dict[str, tuple[float, float]] = {}  # key → (tokens, last)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self._tokens.get(key, (float(self.burst), now))
        elapsed = now - last
        tokens = min(float(self.burst), tokens + elapsed * self.rate)
        if tokens < 1.0:
            self._tokens[key] = (tokens, now)
            return False
        self._tokens[key] = (tokens - 1.0, now)
        return True