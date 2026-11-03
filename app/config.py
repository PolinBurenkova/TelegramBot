# app/config.py
"""Настройки приложения «Города+» через pydantic-settings.

Особенности:
- Все секреты — SecretStr. В логи не попадают.
- database_url собирается автоматически, если не задан явно.
- provider_order_* можно переопределить через .env;
  иначе берётся дефолт из app.constants.PROVIDER_CHAINS.
- В production обязателен BOT_TOKEN.
- admin_ids принимает int, "1,2,3", [1,2,3], "" — всё приводит к list[int].
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import PROVIDER_CHAINS


class LoggingSettings(BaseModel):
    """Параметры логирования для app.utils.logger.setup_logging."""

    dir: str = "logs"
    level: str = "INFO"
    rotation_mb: int = 10
    backup_count: int = 5


class Settings(BaseSettings):
    """Единый объект настроек. Создаётся один раз как settings внизу файла."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ==================== Ядро ====================
    bot_token: SecretStr = SecretStr("")
    admin_ids: list[int] = Field(default_factory=list)

    # ==================== Postgres ====================
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "cities_plus"
    db_user: str = "cities"
    db_password: SecretStr = SecretStr("cities")
    database_url: str | None = None
    # Локальный запуск без Postgres: если DSN указывает на postgresql, а порт
    # не отвечает, в dev-режиме настройки переключаются на SQLite-файл.
    db_fallback_sqlite: bool = True
    db_fallback_url: str = "sqlite+aiosqlite:///./data/cities_bot.db"
    # Выставляется валидатором: фактически использован SQLite вместо Postgres.
    db_fallback_used: bool = False

    # ==================== Redis ====================
    redis_url: str = "redis://localhost:6379/0"
    fsm_redis_url: str = "redis://localhost:6379/1"

    # ==================== Приложение ====================
    log_level: str = "INFO"
    environment: Literal["development", "production", "test"] = "development"
    cache_ttl_default: int = 3_600
    # Секунд на ход в режиме «Города» (0 — без ограничения).
    move_timeout: int = 60
    default_locale: str = "ru"
    use_webhook: bool = False
    webhook_url: str | None = None
    webhook_secret: str | None = None
    # Прокси для Telegram Bot API (например socks5://127.0.0.1:1080 или
    # http://user:pass@host:3128). Нужен там, где api.telegram.org недоступен
    # напрямую: без прокси aiogram падает с TelegramNetworkError.
    bot_proxy: str | None = None
    # Таймаут одного запроса к Telegram, секунды (по умолчанию 60).
    bot_request_timeout: float = 60.0
    # Разрешать только один экземпляр бота на машине (лок-файл data/bot.lock).
    # Второй запуск иначе забирает getUpdates и получает TelegramConflictError.
    bot_single_instance: bool = True
    # Если прокси из BOT_PROXY недоступен — продолжать без него (предупреждение
    # в лог). Удобно, когда переменная окружения осталась от VPN-сессии, а
    # прокси-клиент не запущен. false — падать с ProxyUnavailableError.
    bot_proxy_fallback_direct: bool = True
    # Транспорт до api.telegram.org: auto (по умолчанию), direct или proxy.
    # auto: сначала пробуем прямое соединение (обычный системный VPN маршрутизирует
    # трафик сам, настройка боту не нужна), при неудаче — прокси из BOT_PROXY.
    bot_transport: str = "auto"

    # ==================== Геокодеры ====================
    geonames_username: str | None = None
    opencage_api_key: SecretStr | None = None
    positionstack_api_key: SecretStr | None = None
    geoapify_api_key: SecretStr | None = None
    locationiq_api_key: SecretStr | None = None
    mapbox_geocoding_token: SecretStr | None = None
    photon_url: str = "https://photon.komoot.io"
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    overpass_url: str = "https://overpass-api.de/api/interpreter"

    # ==================== Погода ====================
    openweather_api_key: SecretStr | None = None
    weather_api_key: SecretStr | None = None
    weatherstack_api_key: SecretStr | None = None
    visual_crossing_api_key: SecretStr | None = None
    tomorrow_io_api_key: SecretStr | None = None
    weatherbit_api_key: SecretStr | None = None
    meteosource_api_key: SecretStr | None = None
    accuweather_api_key: SecretStr | None = None
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    # ==================== Фото ====================
    unsplash_access_key: SecretStr | None = None
    pexels_api_key: SecretStr | None = None
    pixabay_api_key: SecretStr | None = None
    flickr_api_key: SecretStr | None = None

    # ==================== Карты ====================
    yandex_maps_api_key: SecretStr | None = None
    mapbox_token: SecretStr | None = None
    maptiler_api_key: SecretStr | None = None
    thunderforest_api_key: SecretStr | None = None
    stadia_maps_api_key: SecretStr | None = None
    osm_static_base_url: str = "https://staticmap.openstreetmap.de"

    # ==================== Wiki ====================
    wikipedia_base_url: str = "https://ru.wikipedia.org/api/rest_v1"
    wikidata_base_url: str = "https://www.wikidata.org/wiki/Special:EntityData"
    wikimedia_commons_base_url: str = "https://commons.wikimedia.org/w/api.php"
    dbpedia_base_url: str = "https://ru.dbpedia.org/sparql"
    wikivoyage_base_url: str = "https://ru.wikivoyage.org/api/rest_v1"

    # ==================== Страны ====================
    rest_countries_base_url: str = "https://restcountries.com/v3.1"
    flagcdn_base_url: str = "https://flagcdn.com"
    flagsapi_base_url: str = "https://flagsapi.com"
    country_state_city_api_key: SecretStr | None = None

    # ==================== Панорамы ====================
    mapillary_token: SecretStr | None = None
    kartaview_base_url: str = "https://api.openstreetcam.org/2.0"
    google_streetview_api_key: SecretStr | None = None
    panoramax_base_url: str = "https://api.panoramax.xyz/api"
    bing_maps_api_key: SecretStr | None = None
    yandex_panoramas_api_key: SecretStr | None = None

    # ==================== Перевод ====================
    libretranslate_url: str = "http://localhost:5000"
    google_translate_api_key: SecretStr | None = None
    deepl_api_key: SecretStr | None = None
    yandex_translate_api_key: SecretStr | None = None
    mymemory_url: str = "https://api.mymemory.translated.net"

    # ==================== Timezone ====================
    timezonedb_api_key: SecretStr | None = None
    worldtimeapi_base_url: str = "https://worldtimeapi.org/api"

    # ==================== Exchange ====================
    exchangerate_api_key: SecretStr | None = None
    open_exchange_rates_api_key: SecretStr | None = None
    frankfurter_base_url: str = "https://api.frankfurter.app"

    # ==================== Holidays ====================
    nager_date_base_url: str = "https://date.nager.at/api/v3"
    holiday_api_key: SecretStr | None = None

    # ==================== Air quality ====================
    openaq_api_key: SecretStr | None = None
    airvisual_api_key: SecretStr | None = None

    # ==================== POI ====================
    opentripmap_api_key: SecretStr | None = None
    foursquare_api_key: SecretStr | None = None
    yelp_api_key: SecretStr | None = None

    # ==================== Nature ====================
    nasa_api_key: SecretStr | None = None
    carbon_interface_api_key: SecretStr | None = None
    usgs_base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1"
    sunrise_sunset_base_url: str = "https://api.sunrise-sunset.org"

    # ==================== Media ====================
    youtube_api_key: SecretStr | None = None
    vimeo_access_token: SecretStr | None = None
    newsapi_key: SecretStr | None = None
    gnews_key: SecretStr | None = None
    guardian_api_key: SecretStr | None = None

    # ==================== IP geo ====================
    ipapi_base_url: str = "https://ipapi.co"
    abstract_api_key: SecretStr | None = None

    # ==================== Bonus ====================
    world_bank_base_url: str = "https://api.worldbank.org/v2"

    # ==================== Переопределения порядка провайдеров ====================
    # Формат: "provider1,provider2,..." — если None, берётся дефолт из constants.
    provider_order_cities: str | None = None
    provider_order_weather: str | None = None
    provider_order_photo: str | None = None
    provider_order_maps: str | None = None
    provider_order_wiki: str | None = None
    provider_order_countries: str | None = None
    provider_order_panorama: str | None = None
    provider_order_translate: str | None = None
    provider_order_timezone: str | None = None
    provider_order_exchange: str | None = None
    provider_order_holidays: str | None = None
    provider_order_air_quality: str | None = None
    provider_order_poi: str | None = None
    provider_order_nature: str | None = None
    provider_order_media: str | None = None
    provider_order_ip_geo: str | None = None

    # ==================== Валидаторы полей ====================

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: object) -> list[int]:
        """Приводит любое разумное представление к list[int].

        Принимает:
        - None / ""           -> []
        - int (например 123)  -> [123]
        - "1,2,3"             -> [1, 2, 3]
        - "[1,2,3]" (JSON)    -> [1, 2, 3]
        - [1, "2", 3]         -> [1, 2, 3]
        """
        if v is None or v == "":
            return []
        if isinstance(v, bool):
            raise ValueError("admin_ids must not be bool")
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            # JSON-массив в строке: "[1,2,3]"
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON in admin_ids: {v!r}") from exc
                if not isinstance(parsed, list):
                    raise ValueError(f"admin_ids JSON must be a list, got {type(parsed).__name__}")
                return [int(x) for x in parsed]
            # Человеческий формат: "1,2,3" или "123"
            return [int(x.strip()) for x in s.split(",") if x.strip()]
        if isinstance(v, (list, tuple, set)):
            return [int(x) for x in v]
        raise ValueError(
            f"admin_ids must be int, str, or list[int], got {type(v).__name__}"
        )

    @field_validator("db_port", "cache_ttl_default", mode="before")
    @classmethod
    def _parse_int_lenient(cls, v: object) -> int:
        """int-поля: пустая строка -> дефолт? Нет, ошибка; но пробелы убираем."""
        if isinstance(v, str):
            s = v.strip()
            if not s:
                raise ValueError("empty value for int field")
            return int(s)
        return int(v)  # type: ignore[arg-type]

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, v: object) -> str:
        """Development / PRODUCTION / test -> нижний регистр."""
        if isinstance(v, str):
            return v.strip().lower()
        return v  # type: ignore[return-value]

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: object) -> str:
        """info / Debug / WARNING -> верхний регистр."""
        if isinstance(v, str):
            return v.strip().upper()
        return v  # type: ignore[return-value]

    @field_validator("bot_transport", mode="before")
    @classmethod
    def _normalize_transport(cls, v: object) -> str:
        """auto / direct / proxy -> нижний регистр; неизвестное значение -> auto."""
        if isinstance(v, str):
            value = v.strip().lower()
            if value in {"auto", "direct", "proxy"}:
                return value
        return "auto"

    # ==================== Модельные валидаторы ====================

    @model_validator(mode="after")
    def _assemble_database_url(self) -> "Settings":
        """Если database_url не задан явно — собираем из частей."""
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.db_user}:"
                f"{self.db_password.get_secret_value()}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self

    @model_validator(mode="after")
    def _require_bot_token_in_prod(self) -> "Settings":
        """В production пустой BOT_TOKEN — ошибка старта."""
        if self.environment == "production" and not self.bot_token.get_secret_value():
            raise ValueError("BOT_TOKEN is required in production")
        return self

    @model_validator(mode="after")
    def _fallback_to_sqlite_in_dev(self) -> "Settings":
        """Локально не падать, если PostgreSQL не поднят.

        Если в dev-окружении задан postgres-DSN, а порт не отвечает, настройки
        переключаются на локальный SQLite-файл. Это снимает классическую
        ошибку `asyncpg ... ConnectionRefusedError: [WinError 1225]`, когда в
        `.env` остался Postgres, а сервер не запущен. В production и при
        `DB_FALLBACK_SQLITE=false` поведение прежнее — явная ошибка.
        """
        url = self.database_url or ""
        if (
            self.environment == "production"
            or not self.db_fallback_sqlite
            or not url.startswith("postgresql")
        ):
            return self

        from urllib.parse import urlsplit

        parts = urlsplit(url)
        host = parts.hostname or "localhost"
        port = parts.port or 5432
        if self._db_port_open(host, port):
            return self

        self.database_url = self.db_fallback_url
        self.db_fallback_used = True
        return self

    @staticmethod
    def _db_port_open(host: str, port: int, timeout: float = 0.6) -> bool:
        """Проверить доступность TCP-порта (быстрая синхронная проба)."""
        import socket

        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    # ==================== Свойства ====================

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def async_engine_kwargs(self) -> dict[str, object]:
        """Параметры пула для create_async_engine (SQLite пул не нужен)."""
        url = (self.database_url or "").lower()
        if url.startswith("sqlite"):
            kwargs: dict[str, object] = {"echo": False}
            # SQLite в памяти живёт ровно одно соединение: без StaticPool каждый
            # checkout получил бы пустую БД, и create_all «терялся» бы (актуально
            # для тестов и для локального прогона без файла).
            if ":memory:" in url:
                from sqlalchemy.pool import StaticPool

                kwargs["poolclass"] = StaticPool
                kwargs["connect_args"] = {"check_same_thread": False}
            return kwargs
        return {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "echo": False,
        }

    # ─── Совместимые вложенные представления ───────────────────────────────

    @property
    def bot(self) -> "_BotView":
        """settings.bot.* (token/webhook) для bot_factory и main."""
        return _BotView(self)

    @property
    def redis(self) -> "_RedisView":
        """settings.redis.* для storage/cache."""
        return _RedisView(self)

    @property
    def logging(self) -> LoggingSettings:
        """Параметры логирования для app.utils.logger.setup_logging."""
        return LoggingSettings(level=self.log_level)

    @property
    def database(self) -> "_DatabaseView":
        """settings.database.url."""
        return _DatabaseView(self)

    @property
    def admin(self) -> "_AdminView":
        """settings.admin.ids."""
        return _AdminView(self)

    @property
    def provider_order(self) -> dict[str, list[str]]:
        """Итоговый порядок провайдеров по функциям.

        Для каждой функции из PROVIDER_CHAINS:
        - если задан provider_order_<function> в .env — используем его,
        - иначе — дефолтный список из constants.
        """
        result: dict[str, list[str]] = {}
        for function, default_chain in PROVIDER_CHAINS.items():
            override = getattr(self, f"provider_order_{function}", None)
            if override:
                result[function] = [
                    p.strip() for p in override.split(",") if p.strip()
                ]
            else:
                result[function] = list(default_chain)
        return result


# Синглтон настроек. Импортируется во всех модулях как `from app.config import settings`.
settings = Settings()


def get_settings() -> Settings:
    """Единая точка доступа к синглтону настроек."""
    return settings


# ─── Совместимые вложенные представления (settings.bot.*, settings.redis.*) ───


class _BotView:
    """settings.bot.*"""

    __slots__ = ("_settings",)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def token(self) -> str:
        return self._settings.bot_token.get_secret_value()

    @property
    def webhook_url(self) -> str | None:
        return self._settings.webhook_url

    @property
    def webhook_secret(self) -> str | None:
        return self._settings.webhook_secret

    @property
    def use_webhook(self) -> bool:
        return self._settings.use_webhook

    @property
    def proxy(self) -> str | None:
        return self._settings.bot_proxy or None

    @property
    def request_timeout(self) -> float:
        return float(self._settings.bot_request_timeout)

    @property
    def single_instance(self) -> bool:
        return bool(self._settings.bot_single_instance)

    @property
    def proxy_fallback(self) -> bool:
        """Продолжать без прокси, если он недоступен (BOT_PROXY_FALLBACK_DIRECT)."""
        return bool(self._settings.bot_proxy_fallback_direct)

    @property
    def transport(self) -> str:
        """Транспорт до Telegram: auto | direct | proxy (BOT_TRANSPORT)."""
        return self._settings.bot_transport or "auto"


class _RedisView:
    """settings.redis.*"""

    __slots__ = ("_settings",)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def url(self) -> str:
        return (self._settings.redis_url or "").strip()

    @property
    def state_ttl(self) -> int:
        return 3_600

    @property
    def data_ttl(self) -> int:
        return 86_400


class _DatabaseView:
    """settings.database.*"""

    __slots__ = ("_settings",)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def url(self) -> str:
        return self._settings.database_url or ""


class _AdminView:
    """settings.admin.*"""

    __slots__ = ("_settings",)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def ids(self) -> list[int]:
        return list(self._settings.admin_ids)