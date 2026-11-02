"""Обогащение данных города: погода, фото, описание, карта."""

from typing import Any

from loguru import logger

from app.constants import CACHE_TTL_PHOTO, CACHE_TTL_WIKI, CACHE_TTL_WEATHER
from app.services.external.open_meteo import OpenMeteoProvider
from app.services.external.openweather import OpenWeatherProvider
from app.services.external.wikimedia import WikimediaProvider
from app.services.external.wiki import WikiProvider
from app.utils.cache import get_cache
from app.utils.cache_keys import photo_key, weather_key, wiki_key
from app.services.external.registry import build_chain


class CityEnrichment:
    """Собирает данные о городе из нескольких API."""

    def __init__(self) -> None:
        self._cache = get_cache()
        self._weather_chain = build_chain(
            "weather", [OpenWeatherProvider(), OpenMeteoProvider()]
        )
        self._wiki = WikiProvider()
        self._wikimedia = WikimediaProvider()

    async def enrich(self, city: dict[str, Any]) -> dict[str, Any]:
        city_id = city.get("geonames_id")
        enriched = dict(city)

        enriched["weather"] = await self._get_weather(city)
        enriched["description"] = await self._get_description(city)
        enriched["photo"] = await self._get_photo(city)
        return enriched

    async def _get_weather(self, city: dict[str, Any]) -> dict[str, Any] | None:
        lat, lon = city.get("lat"), city.get("lon")
        if lat is None or lon is None:
            return None

        cache_key = weather_key(int(city.get("geonames_id") or 0))
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = await self._weather_chain.call("fetch", lat=lat, lon=lon)
        except Exception as exc:
            logger.warning(f"Weather failed: {exc}")
            return None
        # Каскад возвращает ChainResult — сервису нужен только value.
        weather = getattr(result, "value", result)

        if weather:
            await self._cache.set(cache_key, weather, ttl=CACHE_TTL_WEATHER)
        return weather

    async def _get_description(self, city: dict[str, Any]) -> str | None:
        name = city.get("name_ru") or city.get("name")
        if not name:
            return None

        cache_key = wiki_key(name)
        cached = await self._cache.get(cache_key)
        if cached:
            return cached.get("extract") if isinstance(cached, dict) else cached

        try:
            description = await self._wiki.call("get_summary", title=name)
        except Exception as exc:
            logger.warning(f"Wiki failed: {exc}")
            return None

        if description:
            await self._cache.set(cache_key, {"extract": description}, ttl=CACHE_TTL_WIKI)
        return description

    async def _get_photo(self, city: dict[str, Any]) -> str | None:
        name = city.get("name_ru") or city.get("name")
        if not name:
            return None

        cache_key = photo_key(int(city.get("geonames_id") or 0))
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        try:
            url = await self._wikimedia.call("get_photo", query=name)
        except Exception as exc:
            logger.warning(f"Wikimedia failed: {exc}")
            return None

        if url:
            await self._cache.set(cache_key, url, ttl=CACHE_TTL_PHOTO)
        return url