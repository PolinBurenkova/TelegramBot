# Деплой и запуск

Документ описывает только те способы запуска, которые зафиксированы в
репозитории: локальный старт на SQLite и стек Docker Compose с PostgreSQL,
Redis и опциональным LibreTranslate.

## Требования

- Python 3.12+ — `pyproject.toml`, `requires-python = ">=3.12"`.
- Токен бота от @BotFather — единственный обязательный секрет.
- Для контейнерного варианта: Docker Engine и Compose v2.

## Локальный запуск

```bash
python -m pip install -r requirements.txt
copy .env.example .env        # Linux/macOS: cp .env.example .env
# в .env указать BOT_TOKEN и ADMIN_IDS
python -m app.main
```

Альтернативная точка входа — `python run.py` (только polling: webhook там не
поддерживается). Первый старт создаёт схему через `init_models()` в файле
`data/cities_bot.db` (`DATABASE_URL` по умолчанию —
`sqlite+aiosqlite:///./data/cities_bot.db`). Пустые `REDIS_URL`/`FSM_REDIS_URL`
включают `InMemoryRedis` и `MemoryStorage`: кеш и состояния FSM живут в памяти и
теряются при перезапуске, поэтому для одного инстанса этого достаточно, для
нескольких — нет.

## Переменные окружения

Полный список — `.env.example` (69 строк), разбор — `app/config.py` (класс `Settings`).

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | токен Telegram | обязательна |
| `ADMIN_IDS` | список telegram id администраторов | пусто |
| `DATABASE_URL` | DSN БД | SQLite в `data/` |
| `REDIS_URL`, `FSM_REDIS_URL` | кеш и FSM | пусто → память |
| `LOG_LEVEL`, `ENVIRONMENT` | логирование, режим | `INFO`, `development` |
| `USE_WEBHOOK`, `WEBHOOK_URL`, `WEBHOOK_SECRET` | webhook-режим | `false` |
| `PROVIDER_ORDER_*` | порядок провайдеров в цепочках | `PROVIDER_CHAINS` |
| `GEONAMES_USERNAME`, `OPENCAGE_API_KEY`, `OPENWEATHER_API_KEY` и др. | ключи провайдеров | пусто → провайдер не используется |

Провайдеры без ключей (nominatim, open_meteo, wikipedia, rest_countries,
flagcdn, kartaview, panoramax) задаются базовыми URL и работают сразу.

## Миграции

- `alembic.ini`: `script_location = migrations`, поле `sqlalchemy.url` пустое.
- Фактический URL подставляет `migrations/env.py` из `app.config.settings.database_url`,
  поэтому миграции и приложение всегда смотрят в одну базу.
- Ревизии: `0001_initial`, `0002_add_geo_locations`, `0003_add_achievements`,
  `0004_add_api_cache`, `0005_add_user_used_cities`, `0006_add_indexes`; head — `0006`.

```bash
alembic upgrade head                       # применить
alembic downgrade -1                       # откатить одну ревизию
alembic revision --autogenerate -m "msg"   # новая ревизия
make migrate / make revision m="msg"
```

`init_models()` (`Base.metadata.create_all`) остаётся для локального старта и
тестов; в production схему ведёт Alembic.

## Docker Compose

`docker compose up --build` поднимает четыре обязательных сервиса и ждёт
готовности зависимостей:

| Сервис | Роль | Особенности |
|---|---|---|
| `postgres` | БД (`postgres:15-alpine`, user/pass `cities`, база `cities_bot`) | healthcheck `pg_isready`, том `postgres_data` |
| `redis` | кеш и FSM (`redis:7-alpine`, `--appendonly yes`) | healthcheck `redis-cli ping`, том `redis_data` |
| `migrate` | `alembic upgrade head` c `env_file: .env` | `restart: "no"` |
| `bot` | приложение, `env_file: .env`, том `./logs:/app/logs` | стартует после `service_completed_successfully` у `migrate` |

LibreTranslate включается только профилем: `docker compose --profile translate up -d`
(`Dockerfile.libretranslate`, порт `5000:5000`, `LT_LOAD_ONLY=ru,en`).

Важно: `.env.example` содержит SQLite-значение `DATABASE_URL`, но для контейнеров
это не проблема — у сервисов `migrate` и `bot` DSN и адреса Redis заданы явным
блоком `environment:` внутри compose, который перекрывает `env_file: .env`:
`DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-cities}:${POSTGRES_PASSWORD:-cities}@postgres:5432/${POSTGRES_DB:-cities_bot}`,
`REDIS_URL=redis://redis:6379/0`, `FSM_REDIS_URL=redis://redis:6379/1`. Поэтому в
`.env` для Docker достаточно заполнить `BOT_TOKEN` (и при желании сменить
`POSTGRES_*`), а локальный SQLite из примера в контейнеры не «просачивается».

## Образ

`Dockerfile` — двухстадийный: builder на `python:3.12-slim` собирает venv
`/opt/venv`, runtime ставит `libpq5 curl`, создаёт непривилегированного
`appuser`, копирует код и запускает `CMD ["python","-m","app.main"]`.
`HEALTHCHECK` — каждые 30 с, таймаут 10 с, стартовый период 20 с, 3 попытки:
`python -m scripts.healthcheck || exit 1`.

## Проверки после деплоя

- `python -m scripts.healthcheck` — 11 шагов (config, imports, database, cache,
  score, users, cities, game_engine, geo_game, providers, dispatcher), отчёт
  `logs/healthcheck.json`, код возврата 0/1.
- `python check.py` — быстрый смоук: исключения, репозитории, импорт всех
  модулей `app`, сборка диспетчера с ≥10 суброутерами.
- `docker compose logs -f bot`, `docker compose ps` — состояние сервисов.
- `make seed` — загрузка городов, стран, достижений и гео-локаций
  (`scripts/load_cities.py`, `load_countries.py`, `seed_achievements.py`,
  `seed_geo_locations.py`); `make reset-db` — пересоздание базы, только для dev.

## Не подтверждено

- Сборка образа и `docker compose up` в этой среде не выполнялись (`python.exe` и
  процессы блокируются политикой хоста), поэтому команды выше не прогонялись.
- `.dockerignore` пуст (0 байт), а `Dockerfile` делает `COPY . .` — в образ попадут
  `.env`, `.venv`, `data/`, `tests/`, то есть возможна утечка секретов и лишний вес.
- Базовый образ `python:3.11-slim` не совпадает с требованием `>=3.12` из
  `pyproject.toml`.
- Webhook-режим в compose не настроен: порт 8080 (`/webhook`) не публикуется.