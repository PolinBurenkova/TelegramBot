---
name: sqlalchemy-async
description: Correct SQLAlchemy 2.0 async persistence for this repo — engine and session factory placement, declarative models, repository/unit-of-work boundaries, eager loading to avoid N+1, and the Alembic strategy with 0001 baseline plus stub revisions.
whenToUse: Adding or changing models, repositories, queries, transactions, session wiring, or Alembic migrations.
---

# SQLAlchemy 2.0 async — house rules

## Engine and session factory

- The async engine lives in `app/models/base.py` (there is no `app/db/` directory in this tree).
- Pattern:

```python
engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
```

- `expire_on_commit=False` is mandatory: otherwise attribute access after commit triggers lazy IO in async code and raises `MissingGreenlet`.
- One session per logical unit of work. In aiogram, the session is created per update by a middleware and closed in a `finally`.
- Never share a session between concurrent tasks; never store a session on a module-level global for request work.

## Models

- Declarative: `class User(Base): __tablename__ = "users"`, attributes as `Mapped[int]` / `mapped_column(primary_key=True)`.
- Nullability in the type: `Mapped[str]` is NOT NULL, `Mapped[str | None]` is nullable. Do not fight it with `nullable=` unless the default differs.
- Defaults at the DB level for created timestamps: `mapped_column(server_default=func.now())`, plus `onupdate=func.now()` where relevant.
- Relationships: `Mapped[list["City"]] = relationship(back_populates="...", lazy="raise")` is the default choice — it forces explicit loading and prevents accidental async lazy loads. Use `lazy="selectin"` only when the relation is always needed.
- Indexes: declare `Index`/`UniqueConstraint` in `__table_args__` with explicit names. Every foreign key queried by filters gets an index.
- Enums and JSON: use `String` + Python enum validation or native PG enum; document the choice in `docs/decisions.md` if it deviates from tree conventions.

## Repositories

- One repository per aggregate (`app/repositories/*_repo.py`), constructed with a session: `UserRepo(session)`.
- Repository methods do queries and return models/DTOs. They **never commit**, never open transactions, never call other repositories.
- 2.0 style only:

```python
stmt = select(User).where(User.telegram_id == telegram_id)
return (await session.execute(stmt)).scalar_one_or_none()
```

- Bulk needs: `insert(...).on_conflict_do_nothing()` (PG dialect) rather than select-then-insert loops.
- List queries always have an explicit ordering and a limit; no unbounded `select(Model)` in handlers.
- Avoid `session.refresh` in loops; load what you need with `options(selectinload(...))`.

## Transactions and units of work

- Services own the transaction; routers/handlers never commit.
- Preferred shape:

```python
async with session.begin():           # one atomic business action
    await repo.add(entity)
    await other_repo.update(...)
```

- For read-only paths no explicit begin is required; for multi-write paths it is.
- Keep transactions short: no HTTP calls, no sleeps, no Telegram API calls inside a transaction.
- Idempotency: unique constraints on natural keys; handle `IntegrityError` by translating into a domain conflict, not by crashing.

## Queries and performance

- Filter on indexed columns; use `exists()` for checks instead of fetching a row.
- Aggregations in SQL (`func.count`, `func.avg`), never in Python over a full table.
- Pagination by keyset (`WHERE id < :cursor ORDER BY id DESC LIMIT :n`) for large tables.
- Use `.stream()` / `yield_per` for batch exports.

## Alembic

- Strategy for this repo: `migrations/versions/0001_initial.py` is written fully and reflects the whole schema at start; `0002`–`0006` are stub revisions (`upgrade()`/`downgrade()` with `pass`), reserving the chain for later work.
- Set a naming convention on `MetaData` so constraint names are deterministic and autogenerate diffs stay clean.
- Every schema change in later phases: edit models, then a real revision file; never edit an applied 0001 again.
- Startup order in Docker: `alembic upgrade head` before the bot process; the app must fail loudly if migrations fail.
- Migrations must be reversible: implement `downgrade()` even if only `pass` for data-adding revisions where reversal is impossible (document why).

## Anti-patterns to reject in review

- `Query` API, `.query(...)`, `session.commit()` inside repositories.
- Lazy relationship access outside `async with` (greenlet errors).
- Session globals reused across updates; engines re-created per call.
- `SELECT *` through ORM loading with N+1 access in handlers.
- Migrations with hardcoded table names copied from another project, or missing `revision`/`down_revision` links.
