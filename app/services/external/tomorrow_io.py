"""Tomorrow.io — текущая погода. Нужен ключ TOMORROW_IO_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

# weatherCode Tomorrow.io → человеческое описание (основные коды)
_TOMORROW_CODES: dict[int, str] = {
    1000: "Ясно",
    1001: "Облачно",
    1100: "Преимущественно ясно",
    1101: "Переменная облачность",
    1102: "Преимущественно облачно",
    2000: "Туман",
    2100: "Слабый туман",
    4000: "Морось",
    4001: "Дождь",
    4200: "Слабый дождь",
    4201: "Сильный дождь",
    5000: "Снег",
    5001: "Мокрый снег",
    5100: "Слабый снег",
    5101: "Сильный снег",
    6000: "Ледяная морось",
    6001: "Ледяной дождь",
    6200: "Слабый ледяной дождь",
    6201: "Сильный ледяной дождь",
    7000: "Ледяная крупа",
    7101: "Сильная ледяная крупа",
    7102: "Слабая ледяная крупа",
    8000: "Гроза",
}


def _to_float(value: Any) -> float | None:
    """Число к float; мусор и пустое значение → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    """Число (влажность, код) к int; мусор и пустое значение → None."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class TomorrowIOProvider(BaseProvider):
    """Timelines API Tomorrow.io: срез timestep=current по координатам."""

    name = "tomorrow_io"
    category = "weather"
    requires_key = True
    base_url = "https://api.tomorrow.io/v4/timelines"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (TOMORROW_IO_API_KEY)."""
        key = get_settings().tomorrow_io_api_key
        return key.get_secret_value() if key else provider_key("tomorrow_io")

    async def fetch(self, lat: float, lon: float, **kwargs: Any) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        payload = await self.get_json(
            self.base_url,
            params={
                "location": f"{lat},{lon}",
                "fields": "temperature,temperatureApparent,humidity,windSpeed,weatherCode",
                "timestep": "current",
                "units": "metric",
                "apikey": self.api_key,
            },
        )
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        timelines = data.get("timelines") if isinstance(data, dict) else None
        if not isinstance(timelines, list) or not timelines:
            return None
        first = timelines[0]
        intervals = first.get("intervals") if isinstance(first, dict) else None
        if not isinstance(intervals, list) or not intervals:
            return None
        interval = intervals[0]
        values = interval.get("values") if isinstance(interval, dict) else None
        if not isinstance(values, dict):
            return None
        code = _to_int(values.get("weatherCode"))
        return {
            "temp": _to_float(values.get("temperature")),
            "feels_like": _to_float(values.get("temperatureApparent")),
            "description": _TOMORROW_CODES.get(code) if code is not None else None,
            "icon": None,
            "humidity": _to_int(values.get("humidity")),
            "wind": _to_float(values.get("windSpeed")),
        }
