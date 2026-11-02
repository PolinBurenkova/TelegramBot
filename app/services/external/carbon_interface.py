"""Carbon Interface — оценка выбросов CO2 (ключ ``CARBON_INTERFACE_API_KEY``).

Endpoint: ``https://www.carboninterface.com/api/v1/estimates``. Это POST с
заголовком ``Authorization: Bearer <key>``, поэтому ``BaseProvider.get_json``
(только GET и без заголовков) здесь не подходит: запрос выполняется через
``httpx.AsyncClient`` внутри провайдера — тот же приём, что и в
``libretranslate.py``. Любая ошибка транспорта или API → ``None``.

Контракт: ``{"co2_kg": float | None, "source": "carbon_interface", "raw": dict}``.
"""
from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.services.external.base import BaseProvider, provider_key


def _to_float(value: Any) -> float | None:
    """Привести значение к float; None/мусор → None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CarbonInterfaceProvider(BaseProvider):
    """Estimates API: по умолчанию считает CO2 для 100 кВт·ч электричества."""

    name = "carbon_interface"
    category = "nature"
    requires_key = True
    base_url = "https://www.carboninterface.com/api/v1/estimates"

    @property
    def api_key(self) -> str | None:
        """Ключ ``CARBON_INTERFACE_API_KEY``."""
        return provider_key("carbon_interface")

    async def fetch(self, **kwargs: Any) -> dict[str, Any] | None:
        """Посчитать выбросы CO2; сбой сети/API → ``None``."""
        key = self.api_key
        if not key:
            return None
        body: dict[str, Any] = {
            "type": kwargs.get("type", "electricity"),
            "electricity_unit": kwargs.get("electricity_unit", "kwh"),
            "electricity_value": kwargs.get("electricity_value", 100.0),
        }
        country = kwargs.get("country")
        if country:
            body["country"] = country
        extra = kwargs.get("extra")
        if isinstance(extra, dict):
            # Дополнительные поля конкретного типа оценки (flight, shipping…).
            body.update(extra)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning("{}: POST /estimates не удался: {}", self.name, exc)
            return None
        if not isinstance(data, dict):
            return None
        node = data.get("data")
        attributes = node.get("attributes") if isinstance(node, dict) else None
        attributes = attributes if isinstance(attributes, dict) else {}
        return {
            "co2_kg": _to_float(attributes.get("carbon_kg")),
            "source": self.name,
            "raw": data,
        }
