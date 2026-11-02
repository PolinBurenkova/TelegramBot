---
name: docker-deploy
description: Package and run the stack with Docker Compose — multi-stage Python image, postgres/redis/libretranslate services with healthchecks, migrations before startup, secrets via env files, local override for dev, and the verification commands that prove `docker compose up` really works.
whenToUse: Editing Dockerfile, docker-compose.yml, .dockerignore, entrypoint scripts, Makefile targets, or verifying that the whole stack boots and the bot answers.
---

# Docker & Compose — house rules

## Dockerfile

- Multi-stage: `builder` installs dependencies into a virtualenv (or wheels), `runtime` copies only the venv + `app/`; no build tools or caches in the final image.
- Pin the base image (`python:3.12-slim` exact tag) and keep it small; install only needed system packages (`libpq5`, `curl` for healthcheck, `tzdata` for timezones).
- `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `PIP_NO_CACHE_DIR=1` so logs stream and the image stays clean.
- Run as a non-root user; `WORKDIR /app`; copy `requirements` first, then code — layer caching matters.
- No secrets in build args or image layers; no `.env` copied; `.dockerignore` excludes `.git`, `.venv`, `__pycache__`, `tests`, `data`, `logs`, `postgres_data`, `redis_data`, `.dsh`.
- `HEALTHCHECK` on the bot is optional, but each infrastructure service must have one.

## Compose

- Services: `bot`, `postgres`, `redis`, optional `libretranslate`, and optional `nginx` — names exactly as the tree describes.
- `depends_on` with `condition: service_healthy` for postgres/redis; never rely on sleep loops.
- Healthchecks: `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` for postgres, `redis-cli ping` for redis, HTTP check for libretranslate.
- Environment from `env_file: .env` plus explicit non-secret defaults; secrets are never inlined in `docker-compose.yml`.
- Volumes: named volumes for `postgres_data` and `redis_data`; bind-mount source only in `docker-compose.override.yml` (dev), which also sets `command: uvicorn/polling --reload` equivalent and mounts `./logs`.
- Restart policy `unless-stopped`; `logging` driver json-file with `max-size`/`max-file` so disks do not fill.
- One network for the stack; services talk by service name (`postgres:5432`), never `localhost` between containers.
- Ports published only for local dev (postgres/redis optional); production config exposes the bot only if needed.

## Startup sequence

- Entrypoint script (or compose `command`): wait for postgres healthy → `alembic upgrade head` → launch `python run.py`.
- Migration failure must abort startup with a non-zero exit, not start the bot against a stale schema.
- `docker compose down` must not lose data; `down -v` is documented as destructive.
- Graceful shutdown: `STOPSIGNAL SIGTERM`, bot handles SIGTERM and closes connections within the grace period.

## Configuration

- All tunables come from env → `app/config.py` (pydantic-settings). Compose only passes variables; no logic in compose.
- `.env.example` is the contract: every variable the app reads is listed with a safe example value.
- Local dev DB/Redis urls differ from compose service names — keep both in `.env.example` with comments.
- Resource limits (`mem_limit`, `cpus`) or `deploy.resources` for the bot and postgres; do not let one runaway cascade starve the host.

## Makefile / scripts

- Targets: `make up`, `make down`, `make logs`, `make migrate`, `make test`, `make shell`, each one short and documented.
- Scripts under `scripts/` are idempotent and fail fast (`set -euo pipefail`).

## Verification (do this, do not assume)

1. `docker compose config` — validates interpolation and schema; must pass.
2. `docker compose build` — image builds from a clean cache when Dockerfile changed.
3. `docker compose up -d` then `docker compose ps` — every service `healthy`.
4. `docker compose logs bot --tail 50` — migrations ran, bot started, no traceback.
5. Send a real update (or run the smoke script) and confirm an answer.
6. `docker compose down` — clean stop, no orphan containers.

Report the exact commands and their key output lines in the phase report.

## Anti-patterns

- `latest` tags, root user, secrets baked into images, `network_mode: host`, blind `sleep 10` waits.
- Migrations run from the bot process in production without gating.
- Compose files with duplicated config instead of `extends`/override.
- Bind-mounting the source over the image in production.