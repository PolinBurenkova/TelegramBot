---
name: provider-cascade
description: Implement and debug the external-API cascade layer — provider base contract, registry, ordered fallback chain, per-call deadline, retry with jitter, rate limiter, quota manager, circuit breaker, Redis caching, normalized schemas, and JSON mocks for tests.
whenToUse: Adding a new external provider, changing fallback order or quotas, debugging flaky third-party APIs, designing caching, or writing mocks/schemas for external data.
---

# Provider cascade — house rules

## Shape of the layer

- Clients: `app/services/external/<domain>/<provider>.py`, one class per provider, HTTP only, no DB and no Telegram calls.
- Contract: `app/services/external/base.py` — an ABC/Protocol with `name`, `supports(...)`, and one async method per capability returning a normalized pydantic DTO from `app/schemas/api_responses/`.
- Registry: maps domain capability → ordered provider classes from settings, so order is configurable, not hardcoded.
- Chain: `app/utils/provider_chain.py` iterates providers, enforces a global deadline, records health, returns the first success, and raises `ProviderExhaustedError` when all fail.
- Runtime state: `app/repositories/provider_repo.py` stores calls, errors, quotas, and health timestamps.
- Resilience primitives live in `app/utils/`: `retry.py`, `rate_limiter.py`, `quota_manager.py`, `circuit_breaker.py`.

## Per-call rules

- Every call has: `aiohttp.ClientTimeout(total=...)` shorter than the cascade deadline, a max attempt count, and a hard `asyncio.timeout` wrapper.
- Retry only idempotent failure modes: 429, 5xx, timeouts, connection resets. Never retry 400/401/403/404.
- Backoff: exponential with full jitter, capped (`min(cap, base * 2**n) * random()`). No fixed sleeps.
- Respect `Retry-After` when the provider sends it; treat it as a quota signal.
- A provider raising a transient error is skipped to the next one; a provider raising a bug (KeyError, ValidationError on our side) is logged at ERROR with the payload, then treated as unavailable for that call.
- Never let one provider's exception type leak into services: translate to `ProviderError`/`ProviderUnavailable`.

## Quotas and circuits

- Quota manager keyed by provider + period (day/month), counters in Redis where available, otherwise DB via `provider_repo`; check before the call, decrement on success AND on quota-consuming 429s per provider semantics.
- Circuit breaker: open after N consecutive failures, half-open after cooldown, close on success. Open circuit means instant skip, no HTTP attempt.
- Rate limiter per provider: token bucket or sliding window; queue-free, fail-fast behavior preferred to unbounded waiting.
- Health state is observable: last success, last error, consecutive failures; expose it for `/health` and admin reports.

## Caching

- Cache read-through in Redis for deterministic queries (geocode of a city, country info, exchange rate for an hour).
- Key = `provider_domain:normalized_query:params_hash`; normalize aggressively (lowercase, strip, transliterate policy documented).
- Negative caching (not found) with short TTL to protect quotas; never cache auth/service errors.
- Include TTL constants next to the provider, not magic numbers sprinkled in code.
- Degrade gracefully: cache hit must not require provider health; cache miss on exhausted cascade returns a typed "temporarily unavailable" result the bot can phrase.

## Data contracts

- Normalize into `app/schemas/api_responses/<domain>.py`; raw provider payloads stay inside the provider class.
- Use `model_config = ConfigDict(extra="ignore")`, `Field(alias=...)` for provider-specific names, and `field_validator` for unit/format fixes.
- Missing optional fields must be `| None`, and consumers must handle them; do not invent defaults that look like real data.
- Every unit/scale is in the field name (`temperature_c`, `distance_km`, `population_count`).

## Testing and mocks

- JSON fixtures live in `tests/mocks/<provider>/<case>.json` and mirror the real response shape.
- Unit tests replace the transport (aiohttp session or client method), never the provider logic; chain tests use fake providers with scripted outcomes (success, timeout, 429, 500, malformed JSON).
- A new provider is done when: contract implemented, normalized schema added, fixture added, chain order updated, quota/circuit tests pass.

## Anti-patterns

- Providers calling each other, or services calling a client directly while bypassing the chain.
- Synchronous `requests`, unbounded retries, bare `except` that hides real failures.
- Retrying non-idempotent calls (e.g. creating a record at a third party).
- Hardcoded API keys or keys in URLs logged in full.
