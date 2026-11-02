"""IQAir AirVisual — качество воздуха по координатам (нужен ключ).

Назначение: отдать AQI (US) и концентрации PM2.5/PM10 ближайшего города.
Ключ обязателен: ``AIRVISUAL_API_KEY``.
https://api.airvisual.com/v2/nearest_city
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider, provider_key

_URL = "https://api.airvisual.com/v2/nearest_city"


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


class AirVisualProvider(BaseProvider):
    """IQAir AirVisual: /v2/nearest_city, ключ AIRVISUAL_API_KEY."""

    name = "airvisual"
    category = "air_quality"
    requires_key = True

    @property
    def api_key(self) -> str | None:
        """Ключ провайдера из окружения."""
        return provider_key("airvisual")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        """AQI и PM по координатам; None без ключа/данных."""
        if not self.api_key:
            return None
        try:
            payload = await self.get_json(
                _URL,
                params={"lat": lat, "lon": lon, "key": self.api_key},
            )
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        current = data.get("current")
        if not isinstance(current, dict):
            return None
        pollution = current.get("pollution")
        if not isinstance(pollution, dict):
            return None
        aqi = _as_int(pollution.get("aqius"))
        if aqi is None:
            aqi = _as_int(pollution.get("aqicn"))
        pm2_5 = _as_float(pollution.get("p2"))
        pm10 = _as_float(pollution.get("p1"))
        if aqi is None and pm2_5 is None and pm10 is None:
            return None
        if aqi is None:
            description = None
        elif aqi <= 50:
            description = "Хорошо"
        elif aqi <= 100:
            description = "Средне"
        else:
            description = "Плохо"
        return {
            "aqi": aqi,
            "description": description,
            "pm2_5": pm2_5,
            "pm10": pm10,
            "source": self.name,
        }
