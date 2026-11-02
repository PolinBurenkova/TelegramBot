# Архитектура «Города+»

## Слои

```
handlers (aiogram routers)  →  services  →  repositories  →  models (SQLAlchemy)
                                   ↘ services/external (HTTP-провайдеры и каскад)
```

Правила:

1. **Хендлеры тонкие**: парсят `callback_data`/текст, вызывают сервис, рендерят ответ.
   Никакого SQL и `httpx` в `app/handlers/`.
2. **Сервисы** содержат бизнес-логику и работают через репозитории; внешние данные
   получают только из `services/external/`.
3. **Репозитории** — единственное место с запросами SQLAlchemy; наследуют `BaseRepo[T]`.
4. **Модели** не знают о сервисах. PK: `BigInteger().with_variant(Integer, "sqlite")`,
   чтобы автоинкремент работал и в PostgreSQL, и в SQLite.

## Потоки

- **Старт бота**: `app/main.py` → `create_bot()` → `create_dispatcher()` →
  `dp.include_router(root_router)` → polling (или webhook).
- **Сессия БД на апдейт**: middleware открывает `AsyncSession` из
  `async_session_factory` и кладёт её в `data["session"]`.
- **Игра «Города»**: `GameService.make_move()` проверяет букву (`last_letter`),
  уникальность города в партии (`UserUsedCityRepo`), начисляет очки
  (`ScoreService`) и подбирает ответ бота (`_pick_bot_city`).
- **GeoGuessr**: `GeoGameService.start()` фиксирует локацию, `check_answer()`
  считает haversine-расстояние и очки, начисляет XP профилю.
- **Внешние API**: `ExternalRegistry.chain_for(kind)` строит `ProviderChain`
  из зарегистрированных провайдеров; вызов идёт по порядку с дедлайном, кэшем,
  квотой и circuit breaker'ом.

## Режимы исполнения

| | Локально | Production |
|---|---|---|
| БД | SQLite (`data/cities_bot.db`), `init_models()` | PostgreSQL + Alembic |
| Кэш | `MemoryCache` | Redis |
| FSM | `MemoryStorage` | `RedisStorage` |
| Обновления | polling | webhook (опционально) |

## Ключевые модули

- `app/config.py` — `Settings` (pydantic-settings) + singleton `get_settings()`;
- `app/database.py` — движок, фабрика сессий, `init_models()`, `dispose_engine()`;
- `app/utils/provider_chain.py` — каскад, `app/utils/quota_manager.py`,
  `app/utils/circuit_breaker.py`, `app/utils/cache_keys.py` — обвязка провайдеров;
- `app/handlers/router.py` — единый `root_router` (15 подроутеров, `errors` и
  `fallback` последними);
- `scripts/healthcheck.py` — офлайн-проверка всех слоёв без сети и Telegram.

ER-диаграмма — [er_diagram.md](er_diagram.md).
