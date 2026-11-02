"""Единый источник правды для бизнес-констант и лимитов провайдеров."""
from __future__ import annotations

# ─── Game rules ───────────────────────────────────────────────────────────
# Ограничение по населению снято: в игру попадают любые города справочника.
# Значение оставлено (0 = без порога) для совместимости с загрузчиками,
# которые читают константу как дефолт `--min-population`.
CITIES_MIN_POPULATION: int = 0
MOVE_TIMEOUT_SECONDS: int = 60
# «й» НЕ отбрасывается: если город заканчивается на «й», следующий должен
# начинаться с «й» (например, «Волжский» → «Йошкар-Ола»).
LETTERS_SKIP: frozenset[str] = frozenset({"ь", "ъ", "ы"})
SCORE_PER_MOVE: int = 10
SCORE_BONUS_RARE_CITY: int = 5

# ─── Levels ───────────────────────────────────────────────────────────────
LEVELS: list[tuple[int, str]] = [
    (0, "Новичок"),
    (50, "Путешественник"),
    (200, "Географ"),
    (500, "Магистр городов"),
    (1000, "Легенда"),
]

# ─── Cache TTL (seconds) ──────────────────────────────────────────────────
CACHE_TTL: dict[str, int] = {
    "city": 86_400,          # 1 day
    "weather": 600,          # 10 min
    "photo": 604_800,        # 7 days
    "static_map": 3_600,     # 1 hour
    "wiki": 86_400,          # 1 day
    "country": 604_800,      # 7 days
    "translate": 604_800,    # 7 days
    "panorama": 3_600,       # 1 hour
}

# ─── Quota limits (single source of truth) ────────────────────────────────
# period: "second" | "minute" | "hour" | "day" | "month" | "unlimited"
QUOTA_LIMITS: dict[str, dict[str, int | str]] = {
    # Geocoding
    "geonames": {"period": "day", "limit": 20_000},
    "nominatim": {"period": "second", "limit": 1},
    "opencage": {"period": "day", "limit": 2_500},
    "positionstack": {"period": "month", "limit": 25_000},
    "geoapify": {"period": "day", "limit": 3_000},
    "locationiq": {"period": "day", "limit": 5_000},
    "mapbox_geocoding": {"period": "month", "limit": 100_000},
    "tomtom": {"period": "day", "limit": 2_500},
    "here": {"period": "month", "limit": 250_000},
    "photon": {"period": "unlimited", "limit": 0},

    # Weather
    "openweather": {"period": "day", "limit": 1_000},
    "open_meteo": {"period": "unlimited", "limit": 0},
    "weather_api": {"period": "month", "limit": 1_000_000},
    "weatherstack": {"period": "month", "limit": 1_000},
    "visual_crossing": {"period": "day", "limit": 1_000},
    "tomorrow_io": {"period": "day", "limit": 500},
    "weatherbit": {"period": "day", "limit": 500},
    "meteosource": {"period": "day", "limit": 500},
    "accuweather": {"period": "day", "limit": 50},

    # Photos / wiki
    "wikimedia": {"period": "unlimited", "limit": 0},
    "wikipedia_ru": {"period": "unlimited", "limit": 0},
    "unsplash": {"period": "hour", "limit": 50},
    "pexels": {"period": "month", "limit": 200},
    "pixabay": {"period": "day", "limit": 500},
    "flickr": {"period": "hour", "limit": 3_600},

    # Static maps
    "osm_static": {"period": "day", "limit": 5_000},
    "yandex_maps": {"period": "day", "limit": 1_000},
    "mapbox": {"period": "month", "limit": 50_000},
    "maptiler": {"period": "month", "limit": 50_000},
    "thunderforest": {"period": "month", "limit": 150_000},
    "stadia": {"period": "day", "limit": 2_000},

    # Countries
    "rest_countries": {"period": "unlimited", "limit": 0},
    "flagcdn": {"period": "unlimited", "limit": 0},
    "flagsapi": {"period": "unlimited", "limit": 0},
    "country_state_city": {"period": "day", "limit": 100},

    # Translation
    "libretranslate": {"period": "unlimited", "limit": 0},
    "google_translate": {"period": "month", "limit": 500_000},
    "deepl": {"period": "month", "limit": 500_000},
    "yandex_translate": {"period": "month", "limit": 1_000_000},
    "microsoft_translator": {"period": "month", "limit": 2_000_000},

    # Time / currency / holidays
    "timezonedb": {"period": "day", "limit": 50},
    "worldtimeapi": {"period": "unlimited", "limit": 0},
    "frankfurter": {"period": "unlimited", "limit": 0},
    "exchangerate_api": {"period": "month", "limit": 100},
    "open_exchange_rates": {"period": "month", "limit": 1_000},
    "nager_date": {"period": "unlimited", "limit": 0},
    "holiday_api": {"period": "month", "limit": 1_000},

    # Air / POI
    "openaq": {"period": "day", "limit": 1_000},
    "airvisual": {"period": "day", "limit": 100},
    "opentripmap": {"period": "day", "limit": 500},
    "foursquare": {"period": "day", "limit": 5_000},
    "yelp": {"period": "day", "limit": 5_000},

    # Extra
    "nasa": {"period": "day", "limit": 1_000},
    "carbon_interface": {"period": "month", "limit": 500},
    "usgs": {"period": "unlimited", "limit": 0},
    "sunrise_sunset": {"period": "unlimited", "limit": 0},
    "youtube": {"period": "day", "limit": 10_000},
    "vimeo": {"period": "day", "limit": 5_000},
    "newsapi": {"period": "day", "limit": 100},
    "gnews": {"period": "day", "limit": 100},
    "guardian": {"period": "day", "limit": 5_000},
    "ipapi": {"period": "day", "limit": 1_000},
    "abstract": {"period": "month", "limit": 250},

    # Panorama
    "mapillary": {"period": "month", "limit": 50_000},
    "kartaview": {"period": "unlimited", "limit": 0},
    "google_streetview": {"period": "month", "limit": 10_000},
    "panoramax": {"period": "unlimited", "limit": 0},
    "bing_maps": {"period": "month", "limit": 10_000},
    "yandex_panoramas": {"period": "day", "limit": 1_000},
}

# ─── Provider chains (defaults; overridable via .env) ─────────────────────
# Имена выровнены с фактическими модулями app/services/external/<name>.py:
# у каскада нет классов-провайдеров для части имён — реестр просто их
# пропускает (см. docs/decisions.md, решение «Каскады ↔ модули»).
PROVIDER_CHAINS: dict[str, list[str]] = {
    "cities": [
        "geonames", "nominatim", "opencage", "positionstack", "geoapify",
        "locationiq", "mapbox_geocoding", "photon", "open_meteo_geocoding",
    ],
    "weather": [
        "openweather", "open_meteo", "weather_api", "weatherstack",
        "visual_crossing", "tomorrow_io", "weatherbit", "meteosource",
        "accuweather",
    ],
    "photo": [
        "wikimedia", "wiki", "unsplash", "pexels", "pixabay", "flickr",
    ],
    "maps": [
        "osm_maps", "yandex_maps", "mapbox", "maptiler",
        "thunderforest", "stadia_maps",
    ],
    "wiki": ["wiki", "wikidata", "wikimedia", "dbpedia", "wikivoyage", "wikipedia_ru"],
    "countries": ["countries", "country_info", "flagcdn", "flagsapi", "country_state_city"],
    "panorama": [
        "mapillary", "kartaview", "google_streetview",
        "panoramax", "bing_streetside", "yandex_panoramas",
    ],
    "translate": [
        "libretranslate", "google_translate", "deepl",
        "yandex_translate", "mymemory",
    ],
    # Дополнительные виды, для которых в Settings заведены поля
    # provider_order_*: раньше они были объявлены, но не попадали в
    # settings.provider_order, потому что отсутствовали здесь.
    "timezone": ["worldtimeapi", "sunrise_sunset", "timezonedb"],
    "exchange": ["frankfurter", "exchangerate", "exchange", "open_exchange_rates"],
    "holidays": ["nager_date", "holiday_api"],
    "air_quality": ["open_meteo_air", "openaq", "airvisual"],
    "poi": ["overpass", "opentripmap", "foursquare", "yelp"],
    "nature": ["usgs_earthquake", "nasa_apod", "world_bank", "carbon_interface"],
    "media": ["gnews", "newsapi", "guardian", "youtube", "vimeo"],
    "ip_geo": ["ipapi", "abstract_api"],
}

# ─── Callback-префиксы (инлайн-клавиатуры) ──────────────────────────────────
CB_MENU_MAIN: str = "menu:main"
CB_MENU_CITIES: str = "menu:cities"
CB_MENU_HELP: str = "menu:help"
CB_MENU_STATS: str = "menu:stats"
CB_CANCEL: str = "cancel"
CB_SURRENDER: str = "cities:give_up"
CB_DIFFICULTY_PREFIX: str = "diff:"
CB_RESET_CONFIRM: str = "reset:confirm"
CB_RESET_CANCEL: str = "reset:cancel"

# ─── Троттлинг ──────────────────────────────────────────────────────────────
THROTTLE_RATE: float = 0.5

# ─── Очки/бонусы «Городов» ──────────────────────────────────────────────────
WIN_BONUS: int = 50
CITY_BASE_POINTS: int = 10
CITY_LENGTH_BONUS_PER_CHAR: int = 1
CITY_DIFFICULTY_MULTIPLIER: dict[str, float] = {
    "easy": 1.0,
    "medium": 1.25,
    "hard": 1.5,
}
CITY_MIN_LENGTH: int = 3

# ─── GeoGuessr ──────────────────────────────────────────────────────────────
GEO_MAX_SCORE: int = 5_000
GEO_DECAY_KM: float = 2_000.0
GEO_MAX_POINTS_PER_ROUND: int = GEO_MAX_SCORE
GEO_SCALE_KM: float = GEO_DECAY_KM
XP_FOR_GEO: int = 10

# ─── XP/уровни ──────────────────────────────────────────────────────────────
MAX_LEVEL: int = 50
XP_LEVEL_BASE: int = 100
XP_LEVEL_EXPONENT: float = 1.5

# ─── Retry ──────────────────────────────────────────────────────────────────
RETRY_ATTEMPTS: int = 3
RETRY_MIN_WAIT: float = 0.5
RETRY_MAX_WAIT: float = 2.0

# ─── Буквы ──────────────────────────────────────────────────────────────────
# Отбрасываются только «немые» окончания, с которых не начинается ни один
# город. «й» остаётся рабочей буквой: «Волжский» → следующий на «й».
SKIPPABLE_LAST_LETTERS: frozenset[str] = frozenset({"ь", "ъ", "ы"})
LETTER_ALIASES: dict[str, str] = {"ё": "е"}

# ─── Персональные TTL-константы (поверх словаря CACHE_TTL) ──────────────────
CACHE_TTL_CITY: int = CACHE_TTL["city"]
CACHE_TTL_WEATHER: int = CACHE_TTL["weather"]
CACHE_TTL_PHOTO: int = CACHE_TTL["photo"]
CACHE_TTL_WIKI: int = CACHE_TTL["wiki"]
CACHE_TTL_COUNTRY: int = CACHE_TTL["country"]

# ─── Достижения ─────────────────────────────────────────────────────────────
ACHIEVEMENT_FIRST_CITY: str = "first_city"
ACHIEVEMENT_FIRST_GAME: str = "first_game"
ACHIEVEMENT_FIRST_WIN: str = "first_win"
ACHIEVEMENT_POLYGLOT: str = "polyglot"
ACHIEVEMENT_TRAVELER: str = "traveler"
ACHIEVEMENT_LEGEND: str = "legend"
ACHIEVEMENT_GEO_MASTER: str = "geo_master"
ACHIEVEMENT_WEATHER_WIZARD: str = "weather_wizard"

ACHIEVEMENTS_REQUIREMENTS: dict[str, int | float] = {
    ACHIEVEMENT_FIRST_CITY: 1,
    ACHIEVEMENT_FIRST_GAME: 1,
    ACHIEVEMENT_FIRST_WIN: 1,
    ACHIEVEMENT_POLYGLOT: 50,
    ACHIEVEMENT_TRAVELER: 10,
    ACHIEVEMENT_LEGEND: 1_000,
    ACHIEVEMENT_GEO_MASTER: 3_000.0,
    ACHIEVEMENT_WEATHER_WIZARD: 20,
}

ACHIEVEMENTS: dict[str, dict[str, str]] = {
    ACHIEVEMENT_FIRST_CITY: {
        "title": "Первый город", "desc": "Назовите свой первый город",
    },
    ACHIEVEMENT_FIRST_GAME: {
        "title": "Первая игра", "desc": "Сыграйте первую партию в «Города»",
    },
    ACHIEVEMENT_FIRST_WIN: {
        "title": "Первая победа", "desc": "Победите бота в «Городах»",
    },
    ACHIEVEMENT_POLYGLOT: {
        "title": "Полиглот", "desc": "Назовите 50 городов",
    },
    ACHIEVEMENT_TRAVELER: {
        "title": "Путешественник", "desc": "Угадайте 10 стран в GeoGuessr",
    },
    ACHIEVEMENT_LEGEND: {
        "title": "Легенда", "desc": "Наберите 1000 XP",
    },
    ACHIEVEMENT_GEO_MASTER: {
        "title": "Мастер GeoGuessr", "desc": "Средний балл раунда 3000+",
    },
    ACHIEVEMENT_WEATHER_WIZARD: {
        "title": "Повелитель погоды", "desc": "20 запросов погоды по городам",
    },
}
