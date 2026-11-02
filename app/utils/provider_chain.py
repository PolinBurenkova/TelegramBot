"""ProviderChain — каскадный вызов провайдеров с учётом breaker + quota.

Порядок:
  1) кэш (делается ВЫШЕ по стеку, в сервисе — до ProviderChain; см. пример §4)
  2) для каждого провайдера: is_configured → breaker → quota → вызов
  3) первый успешный ответ побеждает
  4) все упали → AllProvidersFailedError с накопленными попытками
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from loguru import logger
from redis.asyncio import Redis

from app.exceptions import (
    AllProvidersFailedError,
    ExternalAPIError,
    QuotaExhaustedError,
)
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.quota_manager import QuotaManager

if TYPE_CHECKING:
    # Только для типизации: импорт на рантайме создаёт цикл
    # provider_chain → external.base → services → registry → provider_chain
    from app.services.external.base import BaseProvider

T = TypeVar("T")


@dataclass
class AttemptLog:
    provider: str
    outcome: str           # "success" | "skipped" | "failed"
    reason: str = ""
    latency_ms: int = 0


@dataclass
class ChainResult(Generic[T]):
    value: T
    provider_used: str | None
    latency_ms: int
    attempts: list[AttemptLog] = field(default_factory=list)


class ProviderChain(Generic[T]):
    """Каскад провайдеров одного «типа» (все геокодеры, все погодники…)."""

    def __init__(
        self,
        name: str | list[BaseProvider],
        providers: list[BaseProvider] | None = None,
        quota: QuotaManager | None = None,
        redis: Redis | None = None,
        *,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1,
    ) -> None:
        # Совместимость двух форм вызова:
        #   ProviderChain([...]) и ProviderChain("name", [...], quota, redis)
        if providers is None and isinstance(name, (list, tuple)):
            name, providers = "inline", list(name)
        if redis is None:
            from app.utils.cache import get_redis

            redis = get_redis()  # type: ignore[assignment]
        if quota is None:
            quota = QuotaManager(redis)  # type: ignore[arg-type]
        self._name = name  # type: ignore[assignment]
        self._providers = providers or []
        self._quota = quota
        self._redis = redis
        self._cb_params = dict(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def providers(self) -> list[BaseProvider]:
        return list(self._providers)

    def _breaker(self, provider: BaseProvider) -> CircuitBreaker:
        # breaker можно переиспользовать из провайдера, если он уже создан
        if getattr(provider, "breaker", None) is not None:
            return provider.breaker  # type: ignore[return-value]
        return CircuitBreaker(self._redis, provider.name, **self._cb_params)

    async def call(
        self,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> ChainResult[T]:
        attempts: list[AttemptLog] = []
        chain_started = time.perf_counter()

        for provider in self._providers:
            # 1) не сконфигурирован
            if not provider.is_configured:
                attempts.append(AttemptLog(provider.name, "skipped", "not_configured"))
                continue

            # 2) quota exhausted
            if await self._quota.is_exhausted(provider.name):
                attempts.append(AttemptLog(provider.name, "skipped", "quota_exhausted"))
                logger.bind(chain=self._name, provider=provider.name).info(
                    "skip | chain={} provider={} reason=quota_exhausted",
                    self._name, provider.name,
                )
                continue

            # 3) circuit breaker
            breaker = self._breaker(provider)
            if await breaker.is_open():
                attempts.append(AttemptLog(provider.name, "skipped", "circuit_open"))
                logger.bind(chain=self._name, provider=provider.name).info(
                    "skip | chain={} provider={} reason=circuit_open",
                    self._name, provider.name,
                )
                continue

            # 4) вызов через breaker
            method = getattr(provider, method_name)
            started = time.perf_counter()
            try:
                value: T = await breaker.call(method, *args, **kwargs)
            except QuotaExhaustedError as exc:
                await self._quota.record_usage(provider.name)  # пометит exhausted
                elapsed = int((time.perf_counter() - started) * 1_000)
                attempts.append(AttemptLog(provider.name, "failed", "quota_429", elapsed))
                logger.bind(chain=self._name, provider=provider.name).warning(
                    "fail | chain={} provider={} reason=quota exhausted",
                    self._name, provider.name,
                )
                _ = exc
                continue
            except ExternalAPIError as exc:
                elapsed = int((time.perf_counter() - started) * 1_000)
                attempts.append(
                    AttemptLog(provider.name, "failed", type(exc).__name__, elapsed)
                )
                logger.bind(chain=self._name, provider=provider.name).warning(
                    "fail | chain={} provider={} err={}",
                    self._name, provider.name, exc.message,
                )
                continue
            except Exception as exc:  # noqa: BLE001 — последний рубеж
                elapsed = int((time.perf_counter() - started) * 1_000)
                attempts.append(
                    AttemptLog(provider.name, "failed", type(exc).__name__, elapsed)
                )
                logger.bind(chain=self._name, provider=provider.name).exception(
                    "unexpected failure | chain={} provider={}",
                    self._name, provider.name,
                )
                continue

            # успех
            elapsed = int((time.perf_counter() - started) * 1_000)
            await self._quota.record_usage(provider.name)
            attempts.append(AttemptLog(provider.name, "success", "", elapsed))
            await self._record_metric(provider.name, success=True)
            total = int((time.perf_counter() - chain_started) * 1_000)
            logger.bind(chain=self._name, provider=provider.name).info(
                "success | chain={} provider={} latency={}ms total={}ms",
                self._name, provider.name, elapsed, total,
            )
            return ChainResult(
                value=value,
                provider_used=provider.name,
                latency_ms=total,
                attempts=attempts,
            )

        # все упали
        for a in attempts:
            if a.outcome == "failed":
                await self._record_metric(a.provider, success=False)
        raise AllProvidersFailedError(
            chain_name=self._name,
            attempts=[
                {"provider": a.provider, "outcome": a.outcome, "reason": a.reason}
                for a in attempts
            ],
            user_message="Сервис временно недоступен, но игра продолжается.",
        )

    async def _record_metric(self, provider: str, *, success: bool) -> None:
        kind = "success" if success else "fail"
        key = f"metrics:provider:{provider}:{kind}"
        try:
            await self._redis.incr(key)
            await self._redis.expire(key, 30 * 86_400)
        except Exception:  # noqa: BLE001 — метрики не должны ломать вызов
            pass