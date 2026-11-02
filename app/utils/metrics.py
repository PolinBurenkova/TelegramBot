"""Simple in-memory counters/histograms."""
from __future__ import annotations

from collections import defaultdict


class Metrics:
    """Simple counters."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)
        self.histograms: dict[str, list[float]] = defaultdict(list)

    def inc(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount

    def observe(self, name: str, value: float) -> None:
        self.histograms[name].append(value)

    def snapshot(self) -> dict:
        return {
            "counters": dict(self.counters),
            "histograms": {k: v[-100:] for k, v in self.histograms.items()},
        }


metrics = Metrics()


def inc(name: str, amount: int = 1) -> None:
    """Увеличить счётчик (модульный алиас для middlewares)."""
    metrics.inc(name, amount)


__all__ = ["Metrics", "metrics", "inc"]