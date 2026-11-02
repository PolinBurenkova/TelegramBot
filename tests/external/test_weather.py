"""Внешние погодные провайдеры: Open-Meteo, OpenWeatherMap, WeatherAPI, Visual Crossing.

Все HTTP-вызовы обслуживает ``httpx.MockTransport``; проверяются нормализация
ответов в единый dict, ``None`` для пустых ответов и деградация без ключа.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from app.services.external.open_meteo import OpenMeteoProvider
from app.services.external.openweather import OpenWeatherProvider
from app.services.external.visual_crossing import VisualCrossingProvider
from app.services.external.weather_api import WeatherAPIProvider
from app.utils.provider_chain import ProviderChain

pytestmark = pytest.mark.external

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"

_LAT = 55.75
_LON = 37.62

_VC_SUCCESS = {
    "currentConditions": {
        "temp": 4.3,
        "feelslike": 2.8,
        "humidity": 81,
        "windspeed": 12.6,
        "conditions": "Пасмурно",
    }
}


def _payload(name: str, case: str):
    return json.loads((_MOCKS / name).read_text(encoding="utf-8"))[case]


def _handler(payload, *, status: int = 200, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return handler


@pytest.fixture
def weather_keys(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "openweather_api_key", SecretStr("owm-key"))
    monkeypatch.setattr(settings, "weather_api_key", SecretStr("weather-key"))
    monkeypatch.setattr(settings, "visual_crossing_api_key", SecretStr("vc-key"))
    return settings


async def test_open_meteo_normalizes_current_weather(mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("open_meteo_responses.json", "success"), seen=seen)
    )
    provider = OpenMeteoProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result == {
        "temp": 4.2,
        "feels_like": None,
        "description": "Пасмурно",
        "icon": None,
        "humidity": None,
        "wind": 3.6,
    }
    assert seen[0].url.path.endswith("/forecast")
    params = dict(seen[0].url.params)
    assert params["latitude"] == "55.75"
    assert params["longitude"] == "37.62"
    assert params["current"] == "temperature_2m,weather_code,wind_speed_10m"


async def test_open_meteo_returns_none_when_current_missing(mock_http_factory):
    client = mock_http_factory(
        _handler(_payload("open_meteo_responses.json", "empty"))
    )
    provider = OpenMeteoProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


async def test_openweather_normalizes_current_weather(weather_keys, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("owm_responses.json", "success"), seen=seen)
    )
    provider = OpenWeatherProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result == {
        "temp": 4.1,
        "feels_like": 1.9,
        "description": "пасмурно",
        "icon": "04d",
        "humidity": 78,
        "wind": 4.0,
    }
    params = dict(seen[0].url.params)
    assert params["appid"] == "owm-key"
    assert params["units"] == "metric"
    assert params["lang"] == "ru"


async def test_openweather_returns_none_without_main_block(
    weather_keys, mock_http_factory
):
    client = mock_http_factory(_handler(_payload("owm_responses.json", "empty")))
    provider = OpenWeatherProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


async def test_weather_api_normalizes_current_weather(weather_keys, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("weather_api_responses.json", "success"), seen=seen)
    )
    provider = WeatherAPIProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result == {
        "temp": 4.0,
        "feels_like": 1.5,
        "description": "Пасмурно",
        "icon": None,
        "humidity": 80,
        "wind": 14.4,
    }
    params = dict(seen[0].url.params)
    assert params["q"] == "55.75,37.62"
    assert params["key"] == "weather-key"


async def test_weather_api_returns_none_for_empty_current(weather_keys, mock_http_factory):
    client = mock_http_factory(
        _handler(_payload("weather_api_responses.json", "empty"))
    )
    provider = WeatherAPIProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


async def test_visual_crossing_normalizes_current_conditions(
    weather_keys, mock_http_factory
):
    seen: list[httpx.Request] = []
    client = mock_http_factory(_handler(_VC_SUCCESS, seen=seen))
    provider = VisualCrossingProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result == {
        "temp": 4.3,
        "feels_like": 2.8,
        "description": "Пасмурно",
        "icon": None,
        "humidity": 81,
        "wind": 12.6,
    }
    request = seen[0]
    assert request.url.path.endswith("/55.75,37.62")
    params = dict(request.url.params)
    assert params["key"] == "vc-key"
    assert params["unitGroup"] == "metric"
    assert params["include"] == "current"


async def test_visual_crossing_returns_none_for_empty_conditions(
    weather_keys, mock_http_factory
):
    client = mock_http_factory(_handler({"currentConditions": {}}))
    provider = VisualCrossingProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


@pytest.mark.parametrize(
    ("provider_cls", "field"),
    [
        pytest.param(OpenWeatherProvider, "openweather_api_key", id="openweather"),
        pytest.param(WeatherAPIProvider, "weather_api_key", id="weather-api"),
        pytest.param(
            VisualCrossingProvider, "visual_crossing_api_key", id="visual-crossing"
        ),
    ],
)
async def test_keyed_weather_provider_not_configured_without_key(
    monkeypatch, mock_http_factory, provider_cls, field
):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), field, None)
    provider = provider_cls(http=mock_http_factory(_handler({})))

    assert provider.is_configured is False


async def test_chain_falls_back_from_rejected_open_meteo(
    weather_keys, mock_http_factory, fake_redis
):
    owm_payload = _payload("owm_responses.json", "success")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/forecast"):
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(200, json=owm_payload)

    client = mock_http_factory(handler)
    chain = ProviderChain(
        "weather",
        [OpenMeteoProvider(http=client), OpenWeatherProvider(http=client)],
        redis=fake_redis,
    )

    result = await chain.call("fetch", lat=_LAT, lon=_LON)

    assert result.provider_used == "openweather"
    assert result.value["temp"] == 4.1
    assert [(a.provider, a.outcome) for a in result.attempts] == [
        ("open_meteo", "failed"),
        ("openweather", "success"),
    ]
    assert result.attempts[0].reason == "ExternalAPIError"
