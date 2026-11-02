"""Yandex Static Maps — статическая карта. Нужен ключ YANDEX_MAPS_API_KEY."""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key


class YandexMapsProvider(BaseProvider):
    """Static API Яндекс.Карт: URL собирается без HTTP-запроса.

    Размер ограничен лимитом сервиса 650×450; лишнее обрезается.
    """

    name = "yandex_maps"
    category = "maps"
    requires_key = True
    base_url = "https://static-maps.yandex.ru"

    @property
    def api_key(self) -> str | None:
        """Ключ из Settings, иначе из окружения (YANDEX_MAPS_API_KEY)."""
        key = get_settings().yandex_maps_api_key
        return key.get_secret_value() if key else provider_key("yandex_maps")

    async def fetch(
        self,
        lat: float,
        lon: float,
        zoom: int = 12,
        width: int = 600,
        height: int = 400,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        key = self.api_key
        if not key:
            return None
        size = f"{min(width, 650)}x{min(height, 450)}"
        image_url = (
            f"{self.base_url}/1.x/?ll={lon},{lat}&z={zoom}&size={size}"
            f"&l=map&lang=ru_RU&apikey={key}"
        )
        return {"image_url": image_url, "lat": lat, "lon": lon, "source": self.name}
