---
name: pytest-testing
description: Test the bot properly with pytest — async fixtures, isolation from network and Telegram, database tests against the compose Postgres, scripted provider fakes, parametrization, and a fast/slow marker split so the common loop stays quick.
whenToUse: Adding or fixing tests, making a failing test pass, deciding what to test after a code block, or wiring CI/`make test` targets.
---

# Testing — house rules

## Layout

- Test tree mirrors the app: `tests/test_services/`, `tests/test_repositories/`, `tests/test_utils/`, `tests/test_handlers/`, `tests/mocks/`, `tests/conftest.py`.
- One test module per unit under test; test names state behavior: `test_chain_skips_provider_after_quota_exhausted`.
- JSON fixtures in `tests/mocks/<provider>/<case>.json`; do not inline huge payloads in test bodies.

## Configuration

- `pytest.ini`/`pyproject.toml`: `asyncio_mode = "auto"` so `async def test_*` needs no decorator.
- Markers: `unit` (no I/O), `integration` (DB/Redis/compose), `slow`. Default run: `-m "not integration and not slow"`.
- `asyncio_default_fixture_loop_scope = "function"` unless a session-scoped resource needs otherwise; keep loop scoping consistent with async engine disposal.

## Fixtures

- Prefer explicit fixtures over module-level globals; `conftest.py` holds only shared ones.
- Async fixtures: `@pytest_asyncio.fixture` (or `async def` + auto mode). Yield fixtures clean up in `finally`.
- Fake settings fixture: build `Settings` with dummy values, never read the real `.env` in unit tests.
- Fake provider: a small class with scripted outcomes:

```python
class FakeProvider:
    def __init__(self, *outcomes): self.outcomes = list(outcomes)
    async def fetch(self, query): result = self.outcomes.pop(0); ...
```

- Session fixture for integration: create engine to the test database, `create_all` or run migrations, wrap each test in a transaction and roll back; dispose the engine at the end.

## What to test

- Business rules in services: scoring, validation, cascade fallback, quota/circuit transitions, cache hit/miss.
- Provider normalization: given a real-shaped JSON fixture → expected DTO (this is where schema drift gets caught).
- Repositories: filters, ordering, uniqueness conflicts, upserts.
- Handlers minimally: mock services, assert reply text and state transitions (that a handler calls the right service once).
- Do not test library behavior, pydantic internals, or trivial getters.

## Style

- Arrange–Act–Assert with blank lines between; one behavior per test.
- `pytest.mark.parametrize` for table cases instead of copy-paste tests; give cases `ids`.
- Assert on values and messages, not on mock call order where not required.
- `pytest.raises(ProviderError, match="quota")` for failure paths — every fallback needs a failing-path test.
- No `time.sleep`, no real network, no real Telegram token. Freeze time with a clock injection or monkeypatched `now`.
- Tests must be order-independent and runnable in parallel (`-p xdist`); no shared mutable state.

## Coverage and gates

- Target: services ≥ 90 %, utils ≥ 80 %, repositories and providers covered by at least one happy + one failure test each.
- Run: `python -m pytest -q -m "not integration and not slow"` per block; full suite before reporting a phase done.
- A failing test is a blocker — fix the code or the wrong expectation, never `xfail` it silently.
- Debug artifacts (`.pytest_cache`, coverage files, `__pycache__`) stay out of git.