"""Каскад панорам для GeoGuessr."""

from typing import Any

from loguru import logger

from app.services.external.kartaview import KartaViewProvider
from app.services.external.mapillary import MapillaryProvider
from app.services.external.registry import build_chain


class PanoramaService:
    """Последовательный перебор провайдеров панорам.

    Mapillary требует токен (обычно не сконфигурирован) — рабочий
    бесплатный путь — KartaView. Если все провайдеры недоступны,
    возвращается ``None``: игра продолжается без картинки.
    """

    def __init__(self) -> None:
        self._chain = build_chain(
            "panorama", [MapillaryProvider(), KartaViewProvider()]
        )

    async def get_panorama(self, lat: float, lon: float) -> dict[str, Any] | None:
        """Панорама ближайшей точки или ``None``.

        Каскад вызывает ``BaseProvider.fetch`` (см. app/utils/provider_chain.py),
        результат приходит в ``ChainResult.value``.
        """
        try:
            result = await self._chain.call("fetch", lat=lat, lon=lon)
        except Exception as exc:  # noqa: BLE001 — панорама не критична для игры
            logger.warning(f"Panorama chain failed: {exc}")
            return None
        value: Any = getattr(result, "value", result)
        return value if isinstance(value, dict) else None
