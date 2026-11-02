"""REST Countries (alpha) — данные страны по ISO2-коду. Ключ не нужен.

Эндпоинт: GET settings.rest_countries_base_url/alpha/{code}?fields=...
Разбор идёт через dict.get: схемы RestCountry в проекте нет полей latlng и
translations, а они нужны контракту каскада.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app.config import get_settings
from app.services.external.base import BaseProvider

#: latlng и translations добавляем к короткому набору полей v3.1.
_FIELDS = "name,cca2,capital,population,region,flags,latlng,translations"


class RestCountriesProvider(BaseProvider):
    """GET /v3.1/alpha/{code}: страна по ISO2/ISO3."""

    name = "countries"
    category = "countries"
    requires_key = False

    async def fetch(self, country_code: str, **kwargs: Any) -> dict[str, Any] | None:
        """Нормализованные данные страны или None."""
        if not country_code or not country_code.strip():
            return None
        base = get_settings().rest_countries_base_url.rstrip("/")
        payload = await self.get_json(
            f"{base}/alpha/{quote(country_code.strip())}",
            params={"fields": _FIELDS},
        )
        item = _first_item(payload)
        if item is None:
            return None
        return _normalize_country(item, source="countries")


def _first_item(payload: Any) -> dict[str, Any] | None:
    """REST Countries отвечает списком стран (иногда объектом)."""
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    return first if isinstance(first, dict) else None


def _normalize_country(item: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    """Ответ REST Countries → контракт каскада."""
    names = item.get("name")
    names = names if isinstance(names, dict) else {}
    name_en = _clean_str(names.get("common")) or _clean_str(names.get("official"))
    name_ru = _translation(item, "rus") or name_en
    code = _clean_str(item.get("cca2"))
    if not code and not name_en:
        return None
    population = item.get("population")
    lat, lon = _lat_lon(item.get("latlng"))
    return {
        "code": code.upper() if code else None,
        "name": name_ru or name_en,
        "name_ru": name_ru,
        "name_en": name_en,
        "capital": _first_str(item.get("capital")),
        "population": population if isinstance(population, int) else None,
        "region": _clean_str(item.get("region")),
        "flag_url": _flag_url(item.get("flags")),
        "lat": lat,
        "lon": lon,
        "source": source,
    }


def _translation(item: dict[str, Any], lang: str) -> str | None:
    """name.common из блока translations."""
    translations = item.get("translations")
    if not isinstance(translations, dict):
        return None
    entry = translations.get(lang)
    if not isinstance(entry, dict):
        return None
    return _clean_str(entry.get("common"))


def _flag_url(flags: Any) -> str | None:
    """PNG-флаг предпочтительнее SVG (Telegram охотнее ест png)."""
    if not isinstance(flags, dict):
        return None
    return _clean_str(flags.get("png")) or _clean_str(flags.get("svg"))


def _first_str(value: Any) -> str | None:
    """Первый непустой элемент списка строк (capital)."""
    if not isinstance(value, list):
        return None
    for entry in value:
        text = _clean_str(entry)
        if text:
            return text
    return None


def _lat_lon(value: Any) -> tuple[float | None, float | None]:
    """[lat, lon] из REST Countries."""
    if not isinstance(value, list) or len(value) < 2:
        return None, None
    lat, lon = value[0], value[1]
    if _is_number(lat) and _is_number(lon):
        return float(lat), float(lon)
    return None, None


def _is_number(value: Any) -> bool:
    """True для int/float, но не для bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _clean_str(value: Any) -> str | None:
    """Непустая строка без окружающих пробелов."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
