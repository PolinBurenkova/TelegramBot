# Тестирование

Набор построен на pytest и покрывает доменную логику, репозитории и внешних
провайдеров. Ниже — фактическое состояние: состав, конфигурация, изоляция от
сети и честная оговорка о прогонах.

## Структура `tests/`

```
tests/
├── conftest.py        # корневые фикстуры: settings, session_factory, db_session,
│                      # fake_redis, sample_user, sample_city, mock_http, mock_http_factory
├── pytest.ini         # отдельный конфиг (testpaths = .), addopts = -q --strict-markers
├── .coveragerc        # source = app, fail_under = 0, заглушки внешних провайдеров в omit
├── unit/              # 18 модулей: чистые функции, кеш, пагинация, circuit breaker, конфиг, меню, лок, сид, Update, команды, shutdown
├── integration/       # 8 модулей: репозитории, сервисы, миграции (SQLite in-memory)
├── external/          # 6 модулей: провайдеры через httpx.MockTransport
├── mocks/             # 11 JSON-файлов `*_responses.json` (success/empty/error)
└── fixtures/          # 4 модуля-фабрики: users, cities, games, geo_locations
```

## Что покрыто

| Модуль | Тестов | Предмет проверки |
|---|---|---|
| `unit/test_validators.py` | 8 | `normalize_city`, `last_letter` («Астрахань» → «н», «Волжский» → «й», ь/ъ/ы отбрасываются), `first_letter`, `is_valid_city_name`, `parse_coordinates` |
| `unit/test_geo_score.py` | 6 | `haversine` (ноль, Москва—СПб, симметрия), `calculate_score` (максимум, затухание, неотрицательность) |
| `unit/test_provider_chain.py` | 4 | fallback, `AllProvidersFailedError.attempts`, пропуск `not_configured`/`quota_exhausted`, 429 → следующий провайдер |
| `unit/test_quota_manager.py` | 3 | исчерпание лимита, безлимитный провайдер, `reset()` |
| `unit/test_score_service.py` | 2 | circuit breaker: OPEN после порога, HALF_OPEN после `recovery_timeout` |
| `unit/test_cache.py` | 14 | `MemoryCache`, `InMemoryRedis` (`set(nx=)`, TTL `-2`/`-1`, `expire`, `pipeline().incr().expire()`), `get_or_set` без кеширования `None` |
| `unit/test_circuit_breaker.py` | 10 | CLOSED → OPEN, 4xx не считается отказом (кроме 429), HALF_OPEN |
| `unit/test_datetime_utils.py` | 7 | `to_user_tz` (Europe/Moscow, +3 ч), `humanize_delta`, `date_key` |
| `unit/test_geo_utils.py` | 5 | `haversine` (≈634 км, допуск 5 км), `format_coordinates` |
| `unit/test_pagination.py` | 8 | `paginate` (границы страниц), `clamp_page` и инлайн-клавиатура `pagination_kb` |
| `unit/test_text_utils.py` | 8 | `truncate`, `pluralize` (14 форм), `escape_html` |
| `unit/test_config_db_fallback.py` | 5 | dev-фолбэк БД: PostgreSQL недоступен → SQLite, production и `DB_FALLBACK_SQLITE=false` не подменяют URL |
| `unit/test_menu_keyboard.py` | 5 | reply-клавиатура меню: `is_persistent`, уникальность и полнота текстов, хендлер на каждую кнопку, обработка callback `"back"` |
| `unit/test_single_instance.py` | 3 | лок одного экземпляра бота: захват/освобождение, повторный захват, идемпотентный `release()`, контекстный менеджер |
| `unit/test_cities_seed.py` | 6 | сид городов: плоская структура, обязательные поля, уникальность имён, ≥50 стран, редкие буквы («й», «ц», «щ», «э», «я»), совпадение зеркала `app/data` |
| `unit/test_event_unwrap.py` | 6 | `Update` в middleware: разворачивание в `Message`/`CallbackQuery`, no-op для события, `event_user` для message/callback, `None` без события |
| `unit/test_bot_commands.py` | 5 | меню команд: уникальность и формат имён, лимиты описаний, хендлер под каждую заявленную команду, наличие ключевых команд, непустые описания бота |
| `unit/test_shutdown.py` | 3 | `run.shutdown`: закрывает сессию/storage/лок, не падает при исключениях в `close()`/`release()`, работает без лока |
| `integration/test_repositories.py` | 32 | `BaseRepo`, `GameRepo`, `MoveRepo`, `CityRepo`, `UserRepo`, `GeoLocationRepo`, `UserUsedCityRepo`, `StatsRepo`, `UserAchievementRepo` |
| `integration/test_cities_game.py` | 14 | старт партии (бот-стартер, `moves_count = 1`), город без порога по населению, правило последней буквы, «й» как рабочая буква, повтор города, ход бота на «к» после «Нальчика», `WIN_BONUS`, статус `timeout` |
| `integration/test_geoguessr.py` | 5 | `calculate_score` на дистанциях, `haversine`, выбор локации по сложности |
| `integration/test_achievements.py` | 8 | идемпотентный сид, `unlock`/`list_for_user`, пороги `ACHIEVEMENTS_REQUIREMENTS` |
| `integration/test_leaderboard.py` | 6 | порядок по сумме очков, пустой лидерборд, top-N, равенство очков |
| `integration/test_profile.py` | 8 | дефолты профиля, `set_difficulty`, локаль/уведомления, игнор мусорных значений |
| `integration/test_settings.py` | 8 | дефолты `Settings`, сборка DSN, `provider_order`, `is_production` |
| `integration/test_migrations.py` | 3 | `alembic upgrade head`, `downgrade base`, линейность цепочки и head = `0006` |
| `external/test_geonames.py` | 9 | GeoNames (ключ) и Nominatim (без ключа), нормализация города, каскад `cities` |
| `external/test_weather.py` | 10 | Open-Meteo, OpenWeather, WeatherAPI, Visual Crossing, `not_configured`, каскад |
| `external/test_wiki.py` | 8 | Wikipedia REST (`/page/summary`) и Wikimedia Commons, 429/HTTP-ошибки, пустой ответ |
| `external/test_panorama.py` | 10 | KartaView без ключа, Mapillary с токеном, пропуск `not_configured` в каскаде `panorama` |
| `external/test_maps.py` | 6 | URL/параметры Thunderforest, готовность провайдеров без ключа, каскад `maps` через `Settings.provider_order` |
| `external/test_countries.py` | 8 | схема `RestCountry`, полный каскад `countries`, пустая цепочка → `AllProvidersFailedError` |

Итого **243 тестовые функции** в 32 модулях (108 unit + 84 integration +
51 external); параметризация увеличивает число проверок при запуске.

## Изоляция от сети, БД и Telegram

- Окружение выставляется в `tests/conftest.py` **до** импорта `app.config`:
  `ENVIRONMENT=test`, `DATABASE_URL=sqlite+aiosqlite:///:memory:`, `REDIS_URL=""`,
  `FSM_REDIS_URL=""`, фиктивные `BOT_TOKEN`/`ADMIN_IDS`. Реальный `.env` не читается.
- БД — SQLite in-memory; для неё `Settings.async_engine_kwargs` подставляет
  `StaticPool` + `check_same_thread=False`, иначе каждая сессия получала бы
  собственную пустую базу.
- Redis заменён: `fakeredis` (фикстура `fake_redis`) либо `InMemoryRedis` из
  `app/utils/cache.py`, который включается сам при пустом `REDIS_URL`.
- HTTP подменён `httpx.MockTransport` (`mock_http`, `mock_http_factory`);
  реальных запросов к внешним API нет. Провайдеры с ключами проверяются как
  `is_configured == False` и не фальсифицируются.
- Telegram не поднимается: тесты не создают `Bot`/`Dispatcher` и не импортируют
  хендлеры.
- `tests/conftest.py` добавляет корень репозитория в `sys.path`, потому что
  `tests/pytest.ini` перехватывает rootdir и `pythonpath` из `pyproject.toml`
  тогда не применяется.

## Конфигурация

- `pyproject.toml`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`,
  `pythonpath = ["."]`, `addopts = "-q --strict-markers"`, маркеры
  `integration`, `external`, `slow`.
- `tests/pytest.ini` (не изменялся): `testpaths = .`, те же маркеры,
  `filterwarnings = ignore::DeprecationWarning`.
- Два конфига с разными `testpaths`; при запуске из корня действует
  `pyproject.toml`, внутри `tests/` — `tests/pytest.ini`. Единый источник не
  выбран (правка `pytest.ini` запрещена правилами проекта).
- Маркер `unit` сознательно не используется: `--strict-markers` уронил бы сбор,
  разделение fast/slow сделано каталогами. Маркер `slow` пока не используется.

## Как запускать

```bash
python -m pip install -r requirements-dev.txt
python -m pytest                                      # весь набор
python -m pytest tests/unit -q                        # только быстрые
python -m pytest tests/integration -m integration     # БД и миграции (SQLite in-memory)
python -m pytest tests/external -m external           # провайдеры на MockTransport
make test                                             # pytest -q
make test-cov                                         # coverage → term-missing + html
```

Чтобы проверить интеграционные тесты на Postgres, задайте `DATABASE_URL` на
поднятый compose-сервис; набор по умолчанию этого не требует.

## Не подтверждено

- **pytest в этой среде ни разу не запускался**: создание процесса запрещено
  политикой хоста (`.venv\Scripts\python.exe`, `python.exe`, `cmd.exe`, `docker`
  → «Отказано в доступе»). Все утверждения выше получены чтением кода: импорты
  и символы проверены статическим чекером (539 импортов, 0 отсутствующих
  модулей и символов), но фактическая коллекция, порядок фикстур, синтаксис при
  исполнении и результат тестов неизвестны.
- Прогон нужно выполнить на обычной машине: `python -m pytest tests -q`.
- `tests/.pytest_cache` содержит следы постороннего прогона (9 тестов, 4
  падения) — это **не** результат текущего дерева и не доказательство ничего.
- Покрытие не измерялось (`fail_under = 0`, отчёт не строился).
