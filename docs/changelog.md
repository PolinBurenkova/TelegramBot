# История изменений

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версионирование —
[SemVer](https://semver.org/lang/ru/). Текущая версия в `pyproject.toml` — `1.0.0`.
Записи восстановлены по состоянию файлов репозитория: git-история и теги в этой
среде недоступны, поэтому даты не указаны.

## [Unreleased]

### Added

- Документация: `docs/deployment.md`, `docs/testing.md`, `docs/security.md`,
  `docs/er_diagram.md`, `docs/changelog.md`, `docs/faq.md`, `docs/decisions.md`,
  `docs/api_integrations.md`; метафайлы репозитория: `.dockerignore`,
  `.editorconfig`, `LICENSE` (MIT), `.vscode/extensions.json`.
- CI/CD: `.github/workflows/ci.yml` (ruff/mypy информативно, блокирующие джобы
  `unit` и `integration` на `python:3.12` + postgres/redis service) и
  `cd.yml` (гейт `vars.DEPLOY_ENABLED == 'true'`, compose-деплой на self-hosted).
- Тестовая инфраструктура: корневой `tests/conftest.py` (фикстуры `settings`,
  `session_factory`, `db_session`, `fake_redis`, `sample_user`, `sample_city`,
  `mock_http`, `mock_http_factory`), `tests/.coveragerc`, `tests/fixtures/*`,
  11 JSON-моков `tests/mocks/*_responses.json`.
- Ограничения по населению сняты: `CITIES_MIN_POPULATION = 0`,
  `CityService.random()` без порога, стартовый город партии — любой,
  `_DIFFICULTY_POPULATION` из GeoGuessr удалён, ежедневное задание без порога,
  `load_cities.py` по умолчанию грузит все города; healthcheck засевает
  замкнутый цикл букв, а тесты фиксируют стартер фикстурой `fixed_starter`.
- Меню снова работает и видно на мобильном: reply-клавиатура помечена
  `is_persistent`, получила `input_field_placeholder`, у всех её кнопок
  появились хендлеры (Играть, GeoGuessr, Профиль, Достижения, Лидерборд,
  Настройки, Помощь), добавлена команда `/menu`; исправлено падение
  `edit_text` с reply-клавиатурой в «В меню»/«Отмена» и оживлён callback
  `"back"`; fallback возвращает меню.
- Правило «й» и таймер хода: «й» больше не считается «немой» буквой
  (`Волжский` → следующий на «й», см. `Йошкар-Ола`); добавлен лимит времени на
  ответ `MOVE_TIMEOUT` (60 с, `0` отключает), таймер с автозавершением партии
  статусом `timeout`, подсказка `⏱ На ответ: N с.` и тексты `game.timer` /
  `game.timeout` в обеих локалях.
- Единое меню команд на мобильном и десктопе: `setup_bot_ui()` при старте
  регистрирует `set_my_commands` (10 команд), кнопку меню `MenuButtonCommands`,
  короткое и полное описание бота; добавлены команды `/play` и `/achievements`,
  чтобы каждый пункт списка реально работал.
- Развёртывание на Debian 13 без Docker: `deploy/deploy_debian13.sh` ставит
  Python 3.13/3.12, PostgreSQL (роль `solar`, база `cities_bot`), Redis и git,
  поднимает venv, применяет миграции, загружает сид городов и включает
  systemd-службу `cities-bot`; повторный запуск обновляет код и перезапускает
  бота. Инструкция — в `docs/deployment.md`.
- Транспорт до Telegram выбирается автоматически (`BOT_TRANSPORT=auto`): при
  включённом обычном системном VPN бот идёт напрямую и не спотыкается о старый
  `BOT_PROXY`; если прямого доступа нет — используется прокси. Режимы `direct`
  и `proxy` фиксируют поведение явно, выбранный транспорт пишется в лог.
- 263 тестовые функции в 34 модулях: `tests/unit` (20 модулей, 128 тестов),
  `tests/integration` (8 модулей, 84 теста), `tests/external` (6 модулей,
  51 тест с `pytest.mark.external`).
- Один экземпляр бота: лок `data/bot.lock` (`app/utils/single_instance.py`),
  ранняя проверка конфликта `ensure_no_polling_conflict()` перед polling и
  понятный `PollingConflictError` вместо бесконечных ретраев
  `TelegramConflictError`; отключается `BOT_SINGLE_INSTANCE=false`.
- Внешние API: все модули-заглушки переведены в рабочие провайдеры (64 нулевых
  файла + `pexels.py`/`timezone.py`), `_PROVIDERS` расширен с 15 до 77 классов,
  `PROVIDER_CHAINS` — с 8 до 16 видов (добавлены `timezone`, `exchange`,
  `holidays`, `air_quality`, `poi`, `nature`, `media`, `ip_geo`); ключи
  «длинного хвоста» читаются через `base.provider_key` по конвенции
  `<NAME>_API_KEY`. Каскад `countries` больше не пустой.
- Прикладные модули: клавиатуры `achievements`/`admin`/`pagination`,
  `notification_service`, `daily_challenge_service`, `export_service`,
  схема `api_responses/google_sv`, `utils/gif` (ffmpeg), middleware `i18n` и
  `metrics`, реальный раздел «Достижения» в `handlers/achievements.py`.
- Рабочие скрипты `scripts/`: `load_cities.py`, `load_countries.py`,
  `load_flags.py`, `load_timezones.py`, `reset_db.py`, `seed_achievements.py`,
  `seed_cities_seed.py`, `seed_geo_locations.py`, `download_dumps.{sh,ps1}`,
  `export_db.sh`, `import_db.sh`.
- Данные: 4 справочника `data/*.json` (страны, ISO-коды, флаги, часовые пояса),
  4 сида `data/seed/*.json` (8 достижений, **112 городов из 70 стран**,
  12 geo-точек, 10 вопросов) и 3 зеркала в `app/data/`.
- Города мира: сид `data/seed/cities_seed.json` расширен до 112 записей в
  русской транслитерации (26 российских + 86 зарубежных: Париж, Лондон, Токио,
  Йоханнесбург, Цюрих, Щецин и др.), поэтому бот отвечает городами любой
  страны; `load_cities.py` по умолчанию грузит **все страны** (`--countries`
  пуст), фильтр по странам остался опциональным.

### Fixed

- `requirements.txt` пересохранён в UTF-8 без BOM (был UTF-16 LE): из-за
  кодировки git считал файл бинарным, а `pip install -r requirements.txt` на
  Linux падал бы с ошибкой декодирования.
- Из репозитория убраны Windows-артефакты `.citiesbot/` (venv) и `run.zip`;
  `.gitignore` дополнен правилами `.citiesbot/`, `.ruff_cache/`, `run.zip`,
  `logs/*.json`, `deploy/*.env`.
- `run.py` / `app/main.py`: корректное завершение при любой ошибке запуска —
  `setup_bot_ui()` и проверка конфликта перенесены внутрь `try`, а в `finally`
  вызывается `run.shutdown()`: закрывает aiohttp-сессию (в т.ч. прокси-коннектор),
  HTTP-клиент, storage и лок. Раньше при 401 сессия не закрывалась, и в консоли
  появлялись `Unclosed connector` и `RuntimeError: Event loop is closed`.
- Прокси из `BOT_PROXY`: `create_session()` заранее проверяет хост:порт
  (`check_proxy_available`) и по умолчанию **продолжает без прокси**, если тот
  недоступен (`BOT_PROXY_FALLBACK_DIRECT=true`, предупреждение в лог) — вместо
  трейсбека `aiohttp_socks.ProxyConnectionError`. Строгий режим
  (`BOT_PROXY_FALLBACK_DIRECT=false`) поднимает `ProxyUnavailableError`. В лог
  пишется `BOT_PROXY: …` с маскировкой пароля (`mask_proxy`).
- `app/bot/middlewares/base.py`: хелперы `unwrap_event()`/`event_user()` —
  middleware на `dp.update` получают `Update`, поэтому `from_user` был `None`;
  `UserContextMiddleware` больше не теряет пользователя (`user`/`profile`/`_`
  снова попадают в `data`), `ThrottlingMiddleware` реально троттлит,
  `I18nMiddleware` берёт `from_user` из вложенного события.
- `app/bot/middlewares/logging.py`: убран `AttributeError: 'functools.partial'
  object has no attribute '__name__'` — имя обработчика берётся безопасно,
  поэтому после каждого ответа больше не приходит «⚠️ Что-то пошло не так».
- `app/handlers/menu.py`: callback-ответы обёрнуты в `_safe_answer()`
  (`query is too old` больше не всплывает как ошибка).
- `app/handlers/cities_game.py`: игра в «Города» отвечает корректно —
  кнопка «🌍 GeoGuessr» и разделы меню (профиль, настройки, достижения)
  снова работают, потому что `user` инжектится middleware.
- `app/bot/middlewares/base.py`: добавлен алиас `BaseMiddleware = BaseBotMiddleware` —
  4 middleware импортировали имя, которого не было (`ImportError` при старте).
- `app/models/game_move.py`: `game_id` приведён к `uuid.UUID` (был `Integer` при
  `games.id` типа `Uuid`), добавлен `UniqueConstraint("game_id", "normalized_name")`.
- `app/config.py`: `async_engine_kwargs` для SQLite in-memory включает `StaticPool`
  и `check_same_thread=False` — иначе каждая сессия видела пустую БД.
- `app/repositories/api_cache_repo.py`: чтение/запись колонки `value` вместо
  несуществующего `payload`.
- `app/repositories/stats_repo.py`: `avg_cities_per_game()` считает
  `avg(Game.moves_count)` — Python-property `cities_count` в SQL не работал;
  `cast(Integer)` получил нормальный импорт.
- `app/repositories/{move_repo,user_achievement_repo}.py`: легаси-шимы переведены
  на декларативный `model = ...` (был `super().__init__(session, Model)` при
  одноаргументном `BaseRepo`).
- `app/main.py`: создание `logs/` и `data/` до первого использования; закрытие
  storage и HTTP-сессии при завершении.
- `app/utils/files.py`: удалён недостижимый `write_text` после `return`.
- `docker-compose.yml`: DSN и Redis-адреса контейнеров заданы явно и не наследуют
  локальный SQLite из `.env`; пароли Postgres параметризованы.
- `Dockerfile`: обе стадии на `python:3.12-slim` (было 3.11), `mkdir -p /app/logs`,
  healthcheck через `python -m scripts.healthcheck`.
- `requirements.txt`: убрано ложное утверждение о «9 зелёных unit-тестах»,
  помечено, что `aiohttp` — транзитивная зависимость aiogram.
- Тесты `tests/external/test_{countries,maps}.py` приведены к новой реальности:
  каскад `countries` проверяется как полный (5 провайдеров без ключей), а не
  пустой; в `maps` проверяются готовность провайдеров без ключа и порядок
  каскада вместо «пропуска отсутствующих модулей».
- Запуск: добавлены `BOT_PROXY` и `BOT_REQUEST_TIMEOUT` (прокси и таймаут
  прокидываются в `AiohttpSession`), `TelegramNetworkError`/401 теперь дают
  понятную подсказку вместо «Fatal error: Request timeout error»; в
  `logs/errors.log` выключен `diagnose`, который печатал значения переменных
  трейсбека (риск утечки токена бота).
- Окружение: `.python-version` исправлен с `3` на `3.12`, `.gitignore`
  игнорирует `.venv-*/`, в `Makefile` добавлены цели `venv`, `run`,
  `healthcheck`, `check`.
- Недоступная БД больше не выглядит ошибкой кода: добавлен dev-fallback на
  SQLite (`DB_FALLBACK_SQLITE`, `DB_FALLBACK_URL`, флаг `db_fallback_used`),
  предупреждение о подмене и готовая инструкция `database_hint()` для
  `ConnectionRefusedError`/`[WinError 1225]`; покрыто
  `tests/unit/test_config_db_fallback.py`.
- `scripts/healthcheck.py`: шаг `game_engine` больше не падает через раз —
  засевается город на «к» (Курск) для ветки стартера «Астрахань», а ход
  пользователя при «нестандартном» стартере выбирается из справочника вместо
  жёсткого словаря; регресс закреплён тестом
  `tests/integration/test_cities_game.py::test_bot_answers_on_k_letter_after_nalchik`.

### Known issues (зафиксировано, не исправлено)

- Запуск тестов, `check.py`, `healthcheck.py`, миграций и Docker в среде разработки
  невозможен: создание процессов заблокировано политикой хоста. Всё перечисленное
  выше проверено только чтением кода и статическим чекером импортов (539 импортов,
  0 отсутствующих модулей и символов).
- `tests/.pytest_cache` хранит следы постороннего прогона (9 тестов, 4 падения);
  к текущему дереву он отношения не имеет.
- Настройки pytest продублированы: `pyproject.toml` (`testpaths = ["tests"]`) и
  `tests/pytest.ini` (`testpaths = .`); `tests/pytest.ini` по правилам проекта не
  правится, коллизия rootdir обойдена `sys.path` в `tests/conftest.py`.
- `app/utils/security.py` и `app/utils/rate_limiter.py` не импортируются нигде —
  реализованы, но не подключены.
- Реализованные провайдеры не проверялись на живых API: часть endpoint'ов и
  имена полей ответов собраны по документации сервисов, разбор защищён
  `.get()`-фолбэками. Ключевые провайдеры без токена пропускаются каскадом —
  это ожидаемое поведение, а не ошибка.
- `app/locales/{ru,en}/LC_MESSAGES/messages.{po,mo}` и `docs/screenshots/*`,
  `docs/er_diagram.png`, `data/cities500.*` остаются пустыми артефактами дерева
  спецификации: локализация реализована на JSON, а дампы и скриншоты нельзя
  сгенерировать в среде без запуска процессов.

## [1.0.0] — дата не зафиксирована

### Added

- Каркас приложения aiogram 3 c асинхронным SQLAlchemy 2: `app/main.py`
  (polling и webhook `/webhook`), `app/bot/` (бот, диспетчер, middlewares,
  фильтры), `app/handlers/` (15 суброутеров, `errors` и `fallback` последними),
  `app/services/`, `app/repositories/` (11 модулей репозиториев на `BaseRepo[T]`),
  `app/models/`, `app/schemas/`, `app/utils/`.
- 12 ORM-моделей: `users`, `profiles`, `games`, `game_moves`, `cities`,
  `user_used_cities`, `achievements`, `user_achievements`, `geo_locations`,
  `api_cache`, `notifications`, `daily_challenges`.
- Alembic: линейная цепочка `0001_initial` → `0006_add_indexes`, head `0006`;
  URL берётся из `app.config.settings.database_url` (`migrations/env.py`).
- Каскад внешних API: реестр 15 провайдеров, 8 цепочек (`cities`, `weather`,
  `photo`, `maps`, `wiki`, `countries`, `panorama`, `translate`), упорядоченный
  fallback с дедлайном, retry с джиттером, `QuotaManager`, circuit breaker,
  кеширование в Redis и `InMemoryRedis` при пустом `REDIS_URL`.
- Игровая логика: «Города+» (последняя буква, антиповтор через
  `user_used_cities`, начисление очков, подбор города бота) и GeoGuessr
  (haversine, XP), достижения и ежедневные задания.
- Инфраструктура запуска: `Dockerfile` (multi-stage, non-root `appuser`,
  `HEALTHCHECK`), `docker-compose.yml` (`postgres`, `redis`, `migrate`, `bot`,
  профиль `translate` для LibreTranslate), `run.py`, `Makefile`
  (`install`, `up`, `migrate`, `seed`, `test`, `lint`, `typecheck`, `reset-db`).
- Диагностика: `scripts/healthcheck.py` (11 шагов, отчёт `logs/healthcheck.json`)
  и `check.py` (исключения, репозитории, импорт всех модулей, сборка диспетчера).
- Наполнение данных: `scripts/load_cities.py`, `load_countries.py`,
  `load_flags.py`, `load_timezones.py`, `seed_achievements.py`,
  `seed_geo_locations.py`, `seed_cities_seed.py`, `data/seed/*.json`.
- Тесты: 26 тестовых функций в 6 модулях (23 unit + 3 integration) — валидаторы,
  гео-скоринг, цепочка провайдеров, менеджер квот, circuit breaker, миграции;
  11 JSON-заготовок ответов провайдеров в `tests/mocks/`.
- Конфигурация качества: `pyproject.toml` (ruff `line-length = 100`, цель py312;
  mypy `python_version = "3.12"`), `requirements.txt`,
  `requirements-dev.txt` (pytest, pytest-asyncio, fakeredis, ruff, mypy),
  `.env.example` (69 строк) с описанием всех переменных.

### Notes

- Единственный сценарий, подтверждённый для «Города+» и GeoGuessr, — unit-уровень
  расчётов и миграций; сквозной прогон бота с реальными провайдерами и Telegram
  не выполнялся.
- `README.md` упоминает `python scripts/healthcheck.py`, а `Dockerfile` и
  `HEALTHCHECK` используют `python -m scripts.healthcheck` — работоспособны оба
  варианта, но документация расходится с образом.