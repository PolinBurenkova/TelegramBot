"""Open-Meteo — погода без ключа (unlimited для некоммерческого usage)."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas.api_responses.open_meteo import OpenMeteoResponse
from app.services.external.base import BaseProvider

# WMO weather codes → человеческое описание
_WMO_CODES: dict[int, str] = {
    0: "Ясно",
    1: "Преимущественно ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    45: "Туман",
    48: "Изморозь",
    51: "Слабая морось",
    53: "Морось",
    55: "Сильная морось",
    61: "Слабый дождь",
    63: "Дождь",
    65: "Сильный дождь",
    71: "Слабый снег",
    73: "Снег",
    75: "Сильный снег",
    80: "Ливни",
    81: "Сильные ливни",
    82: "Очень сильные ливни",
    95: "Гроза",
    96: "Гроза с градом",
    99: "Сильная гроза с градом",
}


class OpenMeteoProvider(BaseProvider):
    """Forecast API. Ключ не нужен — основной погодный провайдер."""

    name = "open_meteo"
    category = "weather"
    requires_key = False

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        base = get_settings().open_meteo_base_url.rstrip("/")
        payload = await self.get_json(
            f"{base}/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
            },
        )
        data = OpenMeteoResponse.model_validate(payload)
        current = data.current
        if current is None:
            return None
        code = current.weather_code
        return {
            "temp": current.temperature_2m,
            "feels_like": None,
            "description": _WMO_CODES.get(code, "—"),
            "icon": None,
            "humidity": None,
            "wind": current.wind_speed_10m,
        }
