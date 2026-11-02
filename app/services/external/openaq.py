"""OpenAQ — измерения качества воздуха (нужен ключ для v3).

Назначение: найти ближайшие станции и вернуть AQI/PM по координатам.
Основной путь — v3 ``/v3/locations`` (требует ``X-API-Key``), резервный —
v2 ``/v2/latest``. Значения в v3 приходят в ``sensors[].latest``, в v2 —
в ``measurements[].value``; поддерживаются оба разбора.
Ключ обязателен: ``OPENAQ_API_KEY``.
API: https://api.openaq.org/v3/locations
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_V3_URL = "https://api.openaq.org/v3/locations"
_V2_URL = "https://api.openaq.org/v2/latest"


def _as_float(value: Any) -> float | None:
    """Число как float, иначе None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    """Целое число, иначе None."""
    number = _as_float(value)
    return None if number is None else int(number)


def _parameter_name(entry: dict[str, Any]) -> str:
    """Имя параметра измерения в нижнем регистре без точки."""
    parameter = entry.get("parameter")
    if isinstance(parameter, dict):
        raw = parameter.get("name")
    else:
        raw = parameter
    text = str(raw).strip().lower() if raw is not None else ""
    return text.replace(".", "")


def _pick(entries: list[dict[str, Any]], names: tuple[str, ...]) -> float | None:
    """Первое непустое значение измерения с подходящим именем параметра."""
    for entry in entries:
        if _parameter_name(entry) not in names:
            continue
        value = entry.get("value")
        if isinstance(value, dict):
            number = _as_float(value.get("value"))
        else:
            number = _as_float(value)
        if number is not None:
            return number
    return None


def _describe(aqi: int | None, pm2_5: float | None) -> str | None:
    """Краткое описание по AQI, иначе по PM2.5."""
    if aqi is not None:
        if aqi > 150:
            return "Очень плохо"
        if aqi > 100:
            return "Плохо"
        if aqi > 50:
            return "Средне"
        return "Хорошо"
    if pm2_5 is not None:
        if pm2_5 > 35:
            return "Плохо"
        if pm2_5 > 12:
            return "Средне"
        return "Хорошо"
    return None


class OpenAQProvider(BaseProvider):
    """OpenAQ: /v3/locations (ключ OPENAQ_API_KEY), фолбэк /v2/latest."""

    name = "openaq"
    category = "air_quality"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения."""
        return provider_key("openaq")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        """Ближайшие измерения по координатам; None без ключа/данных."""
        if not self.api_key:
            return None
        payload = await self._get(
            _V3_URL,
            params={"coordinates": f"{lat},{lon}", "radius": 25000, "limit": 10},
        )
        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list) and results:
                data = self._parse_v3(results)
                if data is not None:
                    return data
        return await self._v2_fallback(lat, lon)

    async def _get(self, url: str, params: dict[str, Any]) -> Any:
        """GET с приведением ошибок провайдера к None."""
        try:
            return await self.get_json(url, params=params)
        except (ExternalAPIError, RateLimitError):
            return None

    def _parse_v3(self, results: list[Any]) -> dict[str, Any] | None:
        """Станции v3: значение лежит в ``sensors[].latest.value``."""
        entries: list[dict[str, Any]] = []
        for station in results:
            if not isinstance(station, dict):
                continue
            sensors = station.get("sensors")
            if not isinstance(sensors, list):
                continue
            for sensor in sensors:
                if not isinstance(sensor, dict):
                    continue
                latest = sensor.get("latest")
                value = latest.get("value") if isinstance(latest, dict) else None
                entries.append({"parameter": sensor.get("parameter"), "value": value})
        return self._package(entries)

    async def _v2_fallback(self, lat: float, lon: float) -> dict[str, Any] | None:
        """v2/latest: измерения по ближайшим станциям."""
        payload = await self._get(
            _V2_URL,
            params={
                "coordinates": f"{lat},{lon}",
                "radius": 25000,
                "limit": 10,
                "parameter": "pm25",
            },
        )
        if not isinstance(payload, dict):
            return None
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None
        entries: list[dict[str, Any]] = []
        for station in results:
            if not isinstance(station, dict):
                continue
            measurements = station.get("measurements")
            if not isinstance(measurements, list):
                continue
            for measurement in measurements:
                if isinstance(measurement, dict):
                    entries.append(measurement)
        return self._package(entries)

    def _package(self, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Собрать нормализованный словарь из измерений."""
        if not entries:
            return None
        pm2_5 = _pick(entries, ("pm25", "pm2_5"))
        pm10 = _pick(entries, ("pm10",))
        aqi = _as_int(_pick(entries, ("aqi", "usaqi", "eaqi", "pm25aqi")))
        if aqi is None and pm2_5 is None and pm10 is None:
            return None
        return {
            "aqi": aqi,
            "description": _describe(aqi, pm2_5),
            "pm2_5": pm2_5,
            "pm10": pm10,
            "source": self.name,
        }
