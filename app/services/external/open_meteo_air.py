"""Open-Meteo Air Quality — качество воздуха по координатам (ключ не нужен).

Назначение: отдать AQI (европейский индекс), человеческое описание и
концентрации PM2.5/PM10 для точки.
Ключ не требуется.
API: https://air-quality-api.open-meteo.com/v1/air-quality
"""
from __future__ import annotations

from typing import Any

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.base import BaseProvider

_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Европейский AQI Open-Meteo → краткое описание
_EAQI_DESCRIPTIONS: dict[int, str] = {
    0: "Очень хорошо",
    1: "Хорошо",
    2: "Средне",
    3: "Плохо",
    4: "Очень плохо",
    5: "Крайне плохо",
}


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


class OpenMeteoAirProvider(BaseProvider):
    """Open-Meteo Air Quality: /v1/air-quality, без ключа."""

    name = "open_meteo_air"
    category = "air_quality"
    requires_key = False

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        """AQI и PM для координаты; None, если данных нет."""
        try:
            payload = await self.get_json(
                _URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": (
                        "european_aqi,us_aqi,pm10,pm2_5,"
                        "carbon_monoxide,nitrogen_dioxide"
                    ),
                },
            )
        except (ExternalAPIError, RateLimitError):
            return None
        if not isinstance(payload, dict):
            return None
        current = payload.get("current")
        if not isinstance(current, dict):
            return None
        aqi = _as_int(current.get("european_aqi"))
        if aqi is None:
            aqi = _as_int(current.get("us_aqi"))
        pm2_5 = _as_float(current.get("pm2_5"))
        pm10 = _as_float(current.get("pm10"))
        if aqi is None and pm2_5 is None and pm10 is None:
            return None
        description = _EAQI_DESCRIPTIONS.get(aqi) if aqi is not None else None
        return {
            "aqi": aqi,
            "description": description,
            "pm2_5": pm2_5,
            "pm10": pm10,
            "source": self.name,
        }
