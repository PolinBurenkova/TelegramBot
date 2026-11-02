Alembic migrations for Cities Plus Bot.

Usage
-----
    alembic upgrade head        # apply all migrations
    alembic downgrade -1        # rollback one revision
    alembic revision --autogenerate -m "message"

Notes
-----
- Online mode only (async engine via app.config).
- Target metadata: app.models.Base.metadata.