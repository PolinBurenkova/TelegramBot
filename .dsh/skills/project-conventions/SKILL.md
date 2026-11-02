---
name: project-conventions
description: Non-negotiable rules for the «Города+» bot repository — file tree authority, layering, typing, secrets, decision log, and the verify-after-each-block workflow. Load before writing or changing any project file.
whenToUse: Any task that creates, edits, or reviews files inside D:\CitiesPlusBot, or that reports on phase progress.
---

# Project conventions — «Города+»

The repository is built to a fixed spec. Follow these rules exactly; do not improvise structure.

## 1. The file tree is the law

- `cities_plus_bot.txt` in the repo root is the **single source of truth** for paths.
- Create only files whose exact paths appear in that tree.
- Paths marked `# ADDED` in the tree (for example `app/repositories/provider_repo.py`, `app/schemas/api_responses/*`) are legal.
- A genuinely new path only happens with a matching line in `docs/decisions.md`:
  `ADDED: <путь> — причина`.
- Never rename, move, or delete a file that already exists. Never "tidy" the tree.
- Imports use tree paths only; no ad-hoc modules, no `app/db/`, no `app/core/`.

## 2. Layering

```
handlers/  -> thin: parse update, call service, render reply. No SQL, no HTTP, no business rules.
services/  -> ALL business logic, orchestration, cascades, caching policy.
repositories/ -> SQLAlchemy queries only; return models or DTOs, never commit decisions.
models/    -> SQLAlchemy 2.0 declarative models + metadata + async engine/session factory.
schemas/   -> pydantic 2 models (API input/output, FSM data, internal DTOs).
keyboards/ -> markup builders only.   fsm/ -> state groups + storage wiring.
external/  -> provider clients (under app/services/external/): HTTP only, no DB access.
utils/     -> pure helpers, no I/O side effects hidden inside.
```

Dependency direction is one-way: `handlers -> services -> repositories -> models`. External clients are called by services, never by handlers or repositories.

## 3. Language and typing rules

- Python 3.12. Use `X | None`, never `Optional[X]`; `list[str]`, `dict[str, int]`, etc.
- Full annotations on every public function, method, and module-level constant. `-> None` for procedures.
- SQLAlchemy 2.0 style: `Mapped[...]`, `mapped_column(...)`, `select()`, `session.execute()`; no legacy `Query`.
- aiogram 3.x APIs only (`Router`, `F`, `Bot`, `Dispatcher`); no aiogram 2 patterns.
- pydantic 2.x (`model_validate`, `model_dump`, `field_validator`, `ConfigDict`); no `.dict()`/`.json()`.
- `from __future__ import annotations` only where it genuinely helps; do not add noise.

## 4. Secrets and config

- Every secret/credential comes from `app/config.py` as a pydantic-settings field with `SecretStr`.
- Never log a secret. If a value must appear in logs, mask it.
- `app/config.py` is the only place that reads `os.environ`; other modules take injected settings.
- `.env` stays untracked; `.env.example` documents keys with dummy values.

## 5. Texts

- User-facing Russian strings either live in code constants or in `app/utils/locales/ru.json`; pick one place per string and keep it there. Never scatter duplicates.

## 6. Decisions log

`docs/decisions.md` records architecture decisions the user asked about and every `ADDED:` path, in the form:

```
## <short title>
Решение: ...
Причина: ...
Альтернативы: ...
```

Update it in the same change as the code it explains.

## 7. Workflow discipline

1. Read the tree file first; confirm the path exists before writing.
2. Implement in small blocks (a layer or a feature), not one giant dump.
3. After each block run a real check:
   - `python -c "import app.<module>"` for new modules,
   - `pytest <test path> -q` for logic,
   - `python -m compileall -q app` for broad syntax safety.
4. Fix failures yourself before moving on. Never report success on an unverified block.
5. Keep `.venv` usage explicit: run checks with the project interpreter, not a random global one.
6. End each phase with a short report: **created / verified / remaining**.

## 8. Definition of done for any code block

- [ ] Paths exist in the tree (or `ADDED:` documented).
- [ ] Imports resolve; type annotations complete.
- [ ] Business logic sits in `services/`.
- [ ] No secret in logs, no hardcoded credentials.
- [ ] Check command run and its output quoted or summarized.
- [ ] `docs/decisions.md` updated when a structural choice was made.
