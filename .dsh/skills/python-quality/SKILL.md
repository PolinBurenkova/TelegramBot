---
name: python-quality
description: Write production-grade Python 3.12 for this repo — modern typing, small pure functions, explicit error handling with typed exceptions, structured logging without secrets, async hygiene, and a review checklist that catches the usual review comments before they happen.
whenToUse: 'Writing or reviewing any .py file: new modules, refactors, bug fixes, or a self-review pass before reporting a block done.'
---

# Python 3.12 quality rules

Target: code a senior reviewer accepts without comments. Optimize for readability and typed contracts, not cleverness.

## Typing

- `X | None`, `list[T]`, `dict[K, V]`, `tuple[A, B]`, `type` aliases with `type Alias = ...`.
- Annotate all parameters, returns, and non-obvious locals. `-> None` is still an annotation.
- Prefer concrete types over `Any`. `Any` in a public signature needs a comment saying why.
- Use `Protocol` for structural seams (e.g. a provider client interface) instead of inheritance chains.
- Use `TypedDict`/`dataclass(frozen=True, slots=True)` for internal records; pydantic for validation boundaries.
- Avoid `# type: ignore`; when unavoidable, add the specific code: `# type: ignore[arg-type]` plus a reason.

## Function and module shape

- One responsibility per module; if a file passes ~400 lines, it is probably doing two jobs.
- Pure functions for transforms; push I/O to the edges (repositories, clients, handlers).
- Early returns beat nested `if`; max nesting depth ~3.
- No mutable default arguments (`def f(x: list = [])`); use `None` + `()/[]/{}` sentinel.
- Keyword-only args for anything with more than two parameters: `def f(*, user_id: int, city: str) -> None`.
- No wildcard imports, no `import *`, no unused imports (ruff enforces).

## Errors

- Define a small exception hierarchy per domain (`ServiceError`, `ProviderError`, `NotFoundError`) instead of raising `ValueError` from deep code.
- Never bare `except:`; catch the narrowest exception, and log with context.
- `raise ... from err` when translating exceptions; preserve the cause.
- Validate at boundaries (pydantic / explicit checks) so inner code can trust its inputs.
- Do not swallow exceptions to "keep things running" — return explicit failure results or re-raise.
- Cleanup goes in `try/finally` or `async with`, not in duplicated code paths.

## Logging

- `log = logging.getLogger(__name__)` at module top; no `print` in app code.
- Log events, not prose: `log.info("provider.failed", extra={"provider": name, "status": code})`-style structured keys.
- Levels: DEBUG for flow detail, INFO for state transitions, WARNING for recoverable degradation, ERROR for failed operations needing attention.
- Never log secrets, tokens, full URLs with keys, or raw user PII. Mask before logging.
- One log line per failure at the level that owns the decision; do not log the same exception at three layers.

## Async hygiene

- Never call blocking I/O (`requests`, `time.sleep`, sync DB drivers, `open` on big files) inside async code; use the async equivalent or `asyncio.to_thread`.
- Always bound network calls with timeouts (`aiohttp.ClientTimeout`, `asyncio.timeout`).
- `asyncio.gather(..., return_exceptions=True)` when partial failure is acceptable, and inspect results.
- Do not create unbounded tasks; keep a set of pending tasks and await/cancel them on shutdown.
- Shared mutable state across tasks needs a lock or immutable design; no "probably fine" races.

## Config and side effects

- Module import must not do I/O, network, or DB connections. Side effects belong in explicit `init()` / lifespan hooks.
- Settings come from `app/config.py` (pydantic-settings, `SecretStr`); never read env vars elsewhere.
- Time and randomness are injectable when tests must be deterministic (`now: datetime | None = None`).

## Self-review checklist

- [ ] Types complete; no `Optional`, no implicit `Any` leaks.
- [ ] Errors typed and translated with `from`.
- [ ] No blocking call in async path; timeouts everywhere.
- [ ] Logs structured, no secrets.
- [ ] No mutable defaults, no dead code, no commented-out blocks.
- [ ] `ruff check <paths>` and `python -m compileall -q app` clean.
- [ ] Names read as domain language (`provider_chain`, `quota_exhausted`), not `process1`, `helper`.
