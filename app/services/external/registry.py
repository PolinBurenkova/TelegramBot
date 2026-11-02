"""Реестр каскадов провайдеров.

ExternalRegistry — единая точка создания каскадов: порядок берётся из
settings.provider_order (PROVIDER_CHAINS + переопределения из .env),
собираются только провайдеры с существующими классами, цепочки кэшируются.
build_chain(...) — для сервисов, собирающих цепочку вручную.

Ключи провайдеров читаются самими классами (Settings или env по конвенции
``<NAME>_API_KEY``, см. ``base.provider_key``); ненастроенные провайдеры
остаются в цепочке, но пропускаются на шаге ``is_configured``.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.external.abstract_api import AbstractAPIProvider
from app.services.external.accuweather import AccuweatherProvider
from app.services.external.airvisual import AirVisualProvider
from app.services.external.bing_streetside import BingStreetsideProvider
from app.services.external.carbon_interface import CarbonInterfaceProvider
from app.services.external.countries import RestCountriesProvider
from app.services.external.country_info import CountryInfoProvider
from app.services.external.country_state_city import CountryStateCityProvider
from app.services.external.dbpedia import DBpediaProvider
from app.services.external.deepl import DeepLProvider
from app.services.external.exchange import ExchangeHostProvider
from app.services.external.exchangerate import ExchangeRateProvider
from app.services.external.flagcdn import FlagCDNProvider
from app.services.external.flagsapi import FlagsAPIProvider
from app.services.external.flickr import FlickrProvider
from app.services.external.foursquare import FoursquareProvider
from app.services.external.frankfurter import FrankfurterProvider
from app.services.external.geoapify import GeoapifyProvider
from app.services.external.geonames import GeoNamesProvider
from app.services.external.gnews import GNewsProvider
from app.services.external.google_streetview import GoogleStreetViewProvider
from app.services.external.google_translate import GoogleTranslateProvider
from app.services.external.guardian import GuardianProvider
from app.services.external.holiday_api import HolidayAPIProvider
from app.services.external.ipapi import IPApiProvider
from app.services.external.kartaview import KartaViewProvider
from app.services.external.libretranslate import LibreTranslateProvider
from app.services.external.locationiq import LocationIQProvider
from app.services.external.mapbox import MapboxProvider
from app.services.external.mapbox_geocoding import MapboxGeocodingProvider
from app.services.external.mapillary import MapillaryProvider
from app.services.external.maptiler import MapTilerProvider
from app.services.external.meteosource import MeteosourceProvider
from app.services.external.mymemory import MyMemoryProvider
from app.services.external.nager_date import NagerDateProvider
from app.services.external.nasa_apod import NasaApodProvider
from app.services.external.newsapi import NewsAPIProvider
from app.services.external.nominatim import NominatimProvider
from app.services.external.open_exchange_rates import OpenExchangeRatesProvider
from app.services.external.open_meteo import OpenMeteoProvider
from app.services.external.open_meteo_air import OpenMeteoAirProvider
from app.services.external.open_meteo_geocoding import OpenMeteoGeocodingProvider
from app.services.external.openaq import OpenAQProvider
from app.services.external.opencage import OpenCageProvider
from app.services.external.opentripmap import OpenTripMapProvider
from app.services.external.openweather import OpenWeatherProvider
from app.services.external.osm_maps import OSMStaticMapProvider
from app.services.external.overpass import OverpassProvider
from app.services.external.panoramax import PanoramaxProvider
from app.services.external.pexels import PexelsProvider
from app.services.external.photon import PhotonProvider
from app.services.external.pixabay import PixabayProvider
from app.services.external.positionstack import PositionstackProvider
from app.services.external.stadia_maps import StadiaMapsProvider
from app.services.external.sunrise_sunset import SunriseSunsetProvider
from app.services.external.thunderforest import ThunderForestProvider
from app.services.external.timezone import TimeZoneDBProvider
from app.services.external.tomorrow_io import TomorrowIOProvider
from app.services.external.unsplash import UnsplashProvider
from app.services.external.usgs_earthquake import USGSEarthquakeProvider
from app.services.external.vimeo import VimeoProvider
from app.services.external.visual_crossing import VisualCrossingProvider
from app.services.external.weather_api import WeatherAPIProvider
from app.services.external.weatherbit import WeatherbitProvider
from app.services.external.weatherstack import WeatherstackProvider
from app.services.external.wiki import WikiProvider
from app.services.external.wikidata import WikidataProvider
from app.services.external.wikimedia import WikimediaProvider
from app.services.external.wikipedia_ru import WikipediaRuProvider
from app.services.external.wikivoyage import WikivoyageProvider
from app.services.external.world_bank import WorldBankProvider
from app.services.external.worldtimeapi import WorldTimeAPIProvider
from app.services.external.yandex_maps import YandexMapsProvider
from app.services.external.yandex_panoramas import YandexPanoramasProvider
from app.services.external.yandex_translate import YandexTranslateProvider
from app.services.external.yelp import YelpProvider
from app.services.external.youtube import YouTubeProvider
from app.utils.cache import get_redis
from app.utils.provider_chain import ProviderChain
from app.utils.quota_manager import QuotaManager

# name из PROVIDER_CHAINS → класс провайдера.
# Полный список: PROVIDER_CHAINS (app/constants.py) ссылается только на эти имена,
# поэтому любая цепочка теперь собирается из реальных классов. Провайдеры,
# требующие ключ, остаются в цепочке и пропускаются, если ключа нет.
_PROVIDERS: dict[str, type[Any]] = {
    # ─── города / геокодинг ────────────────────────────────────────────────
    "geonames": GeoNamesProvider,
    "nominatim": NominatimProvider,
    "opencage": OpenCageProvider,
    "positionstack": PositionstackProvider,
    "geoapify": GeoapifyProvider,
    "locationiq": LocationIQProvider,
    "mapbox_geocoding": MapboxGeocodingProvider,
    "photon": PhotonProvider,
    "open_meteo_geocoding": OpenMeteoGeocodingProvider,
    # ─── погода ────────────────────────────────────────────────────────────
    "open_meteo": OpenMeteoProvider,
    "openweather": OpenWeatherProvider,
    "weather_api": WeatherAPIProvider,
    "visual_crossing": VisualCrossingProvider,
    "weatherstack": WeatherstackProvider,
    "tomorrow_io": TomorrowIOProvider,
    "weatherbit": WeatherbitProvider,
    "meteosource": MeteosourceProvider,
    "accuweather": AccuweatherProvider,
    # ─── фото ──────────────────────────────────────────────────────────────
    "wikimedia": WikimediaProvider,
    "pexels": PexelsProvider,
    "unsplash": UnsplashProvider,
    "pixabay": PixabayProvider,
    "flickr": FlickrProvider,
    # ─── карты ─────────────────────────────────────────────────────────────
    "osm_maps": OSMStaticMapProvider,
    "yandex_maps": YandexMapsProvider,
    "mapbox": MapboxProvider,
    "maptiler": MapTilerProvider,
    "thunderforest": ThunderForestProvider,
    "stadia_maps": StadiaMapsProvider,
    # ─── вики и справочные тексты ──────────────────────────────────────────
    "wiki": WikiProvider,
    "wikidata": WikidataProvider,
    "dbpedia": DBpediaProvider,
    "wikivoyage": WikivoyageProvider,
    "wikipedia_ru": WikipediaRuProvider,
    # ─── страны ────────────────────────────────────────────────────────────
    "countries": RestCountriesProvider,
    "country_info": CountryInfoProvider,
    "flagcdn": FlagCDNProvider,
    "flagsapi": FlagsAPIProvider,
    "country_state_city": CountryStateCityProvider,
    # ─── панорамы ──────────────────────────────────────────────────────────
    "mapillary": MapillaryProvider,
    "kartaview": KartaViewProvider,
    "google_streetview": GoogleStreetViewProvider,
    "panoramax": PanoramaxProvider,
    "bing_streetside": BingStreetsideProvider,
    "yandex_panoramas": YandexPanoramasProvider,
    # ─── перевод ───────────────────────────────────────────────────────────
    "libretranslate": LibreTranslateProvider,
    "google_translate": GoogleTranslateProvider,
    "deepl": DeepLProvider,
    "yandex_translate": YandexTranslateProvider,
    "mymemory": MyMemoryProvider,
    # ─── время и курсы ─────────────────────────────────────────────────────
    "timezonedb": TimeZoneDBProvider,
    "worldtimeapi": WorldTimeAPIProvider,
    "sunrise_sunset": SunriseSunsetProvider,
    "frankfurter": FrankfurterProvider,
    "exchangerate": ExchangeRateProvider,
    "exchange": ExchangeHostProvider,
    "open_exchange_rates": OpenExchangeRatesProvider,
    # ─── праздники и качество воздуха ──────────────────────────────────────
    "nager_date": NagerDateProvider,
    "holiday_api": HolidayAPIProvider,
    "open_meteo_air": OpenMeteoAirProvider,
    "openaq": OpenAQProvider,
    "airvisual": AirVisualProvider,
    # ─── POI, природа, медиа, ip ───────────────────────────────────────────
    "overpass": OverpassProvider,
    "opentripmap": OpenTripMapProvider,
    "foursquare": FoursquareProvider,
    "yelp": YelpProvider,
    "usgs_earthquake": USGSEarthquakeProvider,
    "nasa_apod": NasaApodProvider,
    "world_bank": WorldBankProvider,
    "carbon_interface": CarbonInterfaceProvider,
    "gnews": GNewsProvider,
    "newsapi": NewsAPIProvider,
    "guardian": GuardianProvider,
    "youtube": YouTubeProvider,
    "vimeo": VimeoProvider,
    "ipapi": IPApiProvider,
    "abstract_api": AbstractAPIProvider,
}


def build_chain(name: str, providers: list[Any]) -> ProviderChain:
    """Собрать цепочку с общей квотой и Redis (или in-memory заглушкой)."""
    redis = get_redis()
    return ProviderChain(
        name,
        providers,
        QuotaManager(redis),  # type: ignore[arg-type]
        redis,  # type: ignore[arg-type]
    )


class ExternalRegistry:
    """Каскады внешних API, доступные сервисам."""

    def __init__(
        self,
        http: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._http = http
        self._settings = settings or get_settings()
        self._redis = get_redis()
        self.quota = QuotaManager(self._redis)  # type: ignore[arg-type]
        self._chains: dict[str, ProviderChain] = {}

    def _providers_for(self, function: str) -> list[Any]:
        names = self._settings.provider_order.get(function, [])
        providers: list[Any] = []
        for provider_name in names:
            cls = _PROVIDERS.get(provider_name)
            if cls is None:
                continue  # имени нет в реестре — каскад просто пропускает его
            try:
                providers.append(cls(self._http) if self._http else cls())
            except TypeError:
                providers.append(cls())
        return providers

    def chain_for(self, function: str) -> ProviderChain:
        """Получить (лениво создать) каскад для функции."""
        if function not in self._chains:
            self._chains[function] = ProviderChain(
                function,
                self._providers_for(function),
                self.quota,
                self._redis,  # type: ignore[arg-type]
            )
        return self._chains[function]

    # ─── удобные алиасы ────────────────────────────────────────────────────

    def geocoding_chain(self) -> ProviderChain:
        return self.chain_for("cities")

    def weather_chain(self) -> ProviderChain:
        return self.chain_for("weather")

    def wiki_chain(self) -> ProviderChain:
        return self.chain_for("wiki")

    def photo_chain(self) -> ProviderChain:
        return self.chain_for("photo")

    def panorama_chain(self) -> ProviderChain:
        return self.chain_for("panorama")

    def countries_chain(self) -> ProviderChain:
        return self.chain_for("countries")

    def maps_chain(self) -> ProviderChain:
        return self.chain_for("maps")

    def translate_chain(self) -> ProviderChain:
        return self.chain_for("translate")
