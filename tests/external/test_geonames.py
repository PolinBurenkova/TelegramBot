"""Внешние провайдеры городов: GeoNames (ключ) и Nominatim (без ключа).

Сеть полностью подменена ``httpx.MockTransport``: проверяются разбор ответов,
деградация в ``None`` для «пустых» ответов и каскад ProviderChain.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.exceptions import AllProvidersFailedError, ExternalAPIError, RateLimitError
from app.services.external.geonames import GeoNamesProvider
from app.services.external.nominatim import NominatimProvider
from app.utils.provider_chain import ProviderChain

pytestmark = pytest.mark.external

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"


def _payload(name: str, case: str):
    return json.loads((_MOCKS / name).read_text(encoding="utf-8"))[case]


def _handler_for(payload, *, status: int = 200, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return handler


@pytest.fixture
def geonames_ready(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "geonames_username", "tester")
    return get_settings()


@pytest.fixture
def nominatim_url(monkeypatch) -> str:
    from app.config import get_settings

    url = "https://nominatim.test"
    monkeypatch.setattr(get_settings(), "nominatim_url", url)
    return url


async def test_geonames_fetch_normalizes_city(geonames_ready, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler_for(_payload("geonames_responses.json", "success"), seen=seen)
    )
    provider = GeoNamesProvider(http=client)

    result = await provider.fetch("Москва")

    assert result == {
        "geonames_id": 524901,
        "name": "Moscow",
        "name_ru": "Moscow",
        "country_code": "RU",
        "country_name": "Russia",
        "lat": pytest.approx(55.75222),
        "lon": pytest.approx(37.61556),
        "population": 12506468,
        "timezone": "Europe/Moscow",
        "source": "geonames",
    }
    assert len(seen) == 1
    request = seen[0]
    assert request.url.path == "/searchJSON"
    assert dict(request.url.params) == {
        "q": "Москва",
        "username": "tester",
        "maxRows": "1",
        "featureClass": "P",
        "orderby": "population",
    }


async def test_geonames_fetch_returns_none_for_empty_result(
    geonames_ready, mock_http_factory
):
    client = mock_http_factory(_handler_for(_payload("geonames_responses.json", "empty")))
    provider = GeoNamesProvider(http=client)

    assert await provider.fetch("Нигдеград") is None


async def test_geonames_fetch_returns_none_on_api_status(
    geonames_ready, mock_http_factory
):
    client = mock_http_factory(_handler_for(_payload("geonames_responses.json", "error")))
    provider = GeoNamesProvider(http=client)

    assert await provider.fetch("Москва") is None


async def test_geonames_is_not_configured_without_username(monkeypatch, mock_http_factory):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "geonames_username", "")
    provider = GeoNamesProvider(http=mock_http_factory(_handler_for({})))

    assert provider.is_configured is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(500, ExternalAPIError, id="server-error"),
        pytest.param(429, RateLimitError, id="rate-limited"),
    ],
)
async def test_geonames_maps_http_errors(
    geonames_ready, mock_http_factory, status, expected
):
    client = mock_http_factory(_handler_for({}, status=status))
    provider = GeoNamesProvider(http=client)

    with pytest.raises(expected) as excinfo:
        await provider.fetch("Москва")

    assert excinfo.value.provider == "geonames"
    if status == 429:
        assert "rate limited" in excinfo.value.message
    else:
        assert excinfo.value.status_code == 500
        assert "HTTP 500" in excinfo.value.message


async def test_nominatim_fetch_returns_coordinates(nominatim_url, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler_for(_payload("nominatim_responses.json", "success"), seen=seen)
    )
    provider = NominatimProvider(http=client)

    result = await provider.fetch("Москва")

    assert result is not None
    assert result["name"] == "Москва"
    assert result["lat"] == pytest.approx(55.7558)
    assert result["lon"] == pytest.approx(37.6173)
    assert result["country_code"] is None
    assert result["population"] is None
    assert result["source"] == "nominatim"
    assert seen[0].url.path == "/search"
    assert seen[0].url.host == "nominatim.test"
    assert dict(seen[0].url.params) == {
        "q": "Москва",
        "format": "jsonv2",
        "limit": "1",
        "accept-language": "ru",
    }


async def test_nominatim_fetch_returns_none_for_empty_result(
    nominatim_url, mock_http_factory
):
    client = mock_http_factory(_handler_for(_payload("nominatim_responses.json", "empty")))
    provider = NominatimProvider(http=client)

    assert await provider.fetch("Нигдеград") is None


async def test_chain_falls_back_from_geonames_to_nominatim(
    monkeypatch, nominatim_url, mock_http_factory, fake_redis
):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "geonames_username", "")
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler_for(_payload("nominatim_responses.json", "success"), seen=seen)
    )
    chain = ProviderChain(
        "cities",
        [GeoNamesProvider(http=client), NominatimProvider(http=client)],
        redis=fake_redis,
    )

    result = await chain.call("fetch", query="Москва")

    assert result.provider_used == "nominatim"
    assert result.value["name"] == "Москва"
    assert [(a.provider, a.outcome) for a in result.attempts] == [
        ("geonames", "skipped"),
        ("nominatim", "success"),
    ]
    assert result.attempts[0].reason == "not_configured"
    assert len(seen) == 1


async def test_chain_raises_all_providers_failed(
    monkeypatch, nominatim_url, mock_http_factory, fake_redis
):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "geonames_username", "")
    client = mock_http_factory(_handler_for({}, status=503))
    chain = ProviderChain(
        "cities",
        [GeoNamesProvider(http=client), NominatimProvider(http=client)],
        redis=fake_redis,
    )

    with pytest.raises(AllProvidersFailedError) as excinfo:
        await chain.call("fetch", query="Москва")

    error = excinfo.value
    assert error.chain_name == "cities"
    assert error.attempts == [
        {"provider": "geonames", "outcome": "skipped", "reason": "not_configured"},
        {"provider": "nominatim", "outcome": "failed", "reason": "ExternalAPIError"},
    ]
    assert "временно недоступен" in error.user_message
