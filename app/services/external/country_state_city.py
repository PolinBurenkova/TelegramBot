"""CountriesNow — регионы (states) страны. Ключ не нужен.

GET https://countriesnow.space/api/v0.1/countries/states?country={name}
API ищет страну по названию, поэтому в country_code допускается и код, и
название; при необходимости название можно передать kwarg'ом country.
"""
from __future__ import annotations

from typing import Any

from app.services.external.base import BaseProvider

_API_URL = "https://countriesnow.space/api/v0.1/countries/states"


class CountryStateCityProvider(BaseProvider):
    """Регионы страны списком названий."""

    name = "country_state_city"
    category = "countries"
    requires_key = False

    async def fetch(self, country_code: str, **kwargs: Any) -> dict[str, Any] | None:
        """Список регионов страны или None."""
        raw = kwargs.get("country") or country_code
        if not isinstance(raw, str) or not raw.strip():
            return None
        country = raw.strip()
        payload = await self.get_json(_API_URL, params={"country": country})
        states = _states(payload)
        if not states:
            return None
        return {"code": country, "states": states, "source": "country_state_city"}


def _states(payload: Any) -> list[str]:
    """Названия регионов из data.states (пустой список, если их нет)."""
    if not isinstance(payload, dict) or payload.get("error"):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    raw_states = data.get("states")
    if not isinstance(raw_states, list):
        return []
    states: list[str] = []
    for state in raw_states:
        if isinstance(state, dict):
            name = state.get("name")
        else:
            name = state
        if isinstance(name, str) and name.strip():
            states.append(name.strip())
    return states
