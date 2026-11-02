"""Внешние провайдеры карт: Thunderforest и реестр каскада «maps».

Thunderforest не делает HTTP-запросов — он только собирает URL статической
карты, поэтому транспорт перехватывать нечего: проверяется сам URL и ключ.
"""
from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from app.exceptions import AllProvidersFailedError
from app.services.external.registry import ExternalRegistry
from app.services.external.thunderforest import ThunderForestProvider

pytestmark = pytest.mark.external

_LAT = 55.7558
_LON = 37.6173


def _handler(seen: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    return handler


@pytest.fixture
def maps_key(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "thunderforest_api_key", SecretStr("tf-key"))
    return settings


async def test_thunderforest_builds_default_static_map_url(maps_key, mock_http_factory):
    seen: list[httpx.Request] = []
    provider = ThunderForestProvider(http=mock_http_factory(_handler(seen)))

    result = await provider.fetch(_LAT, _LON)

    assert result is not None
    assert result["lat"] == _LAT
    assert result["lon"] == _LON
    assert result["source"] == "thunderforest"
    assert result["image_url"] == (
        "https://staticmap.thunderforest.com/"
        "?center=55.7558,37.6173&zoom=12&size=600x400&apikey=tf-key"
    )
    assert seen == []  # провайдер не ходит в сеть


async def test_thunderforest_honors_zoom_and_size(maps_key, mock_http_factory):
    seen: list[httpx.Request] = []
    provider = ThunderForestProvider(http=mock_http_factory(_handler(seen)))

    result = await provider.fetch(_LAT, _LON, zoom=16, width=800, height=500)

    assert result is not None
    assert "zoom=16" in result["image_url"]
    assert "size=800x500" in result["image_url"]
    assert "apikey=tf-key" in result["image_url"]


async def test_thunderforest_returns_none_without_key(monkeypatch, mock_http_factory):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "thunderforest_api_key", None)
    seen: list[httpx.Request] = []
    provider = ThunderForestProvider(http=mock_http_factory(_handler(seen)))

    assert provider.is_configured is False
    assert await provider.fetch(_LAT, _LON) is None
    assert seen == []


async def test_maps_chain_skips_providers_without_keys(monkeypatch, mock_http_factory):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "thunderforest_api_key", None)
    chain = ExternalRegistry(
        http=mock_http_factory(_handler([]))
    ).chain_for("maps")

    readiness = {provider.name: provider.is_configured for provider in chain.providers}
    assert readiness["osm_maps"] is True  # ключ не нужен
    assert readiness["thunderforest"] is False  # ключ убран monkeypatch'ем
    assert readiness["yandex_maps"] is False
    assert readiness["mapbox"] is False
    assert readiness["maptiler"] is False
    assert readiness["stadia_maps"] is False


async def test_empty_maps_chain_fails_without_attempts():
    from app.services.external.registry import build_chain

    chain = build_chain("maps", [])

    with pytest.raises(AllProvidersFailedError) as excinfo:
        await chain.call("fetch", lat=_LAT, lon=_LON)

    assert excinfo.value.chain_name == "maps"
    assert excinfo.value.attempts == []


async def test_maps_chain_uses_configured_provider(
    monkeypatch, maps_key, mock_http_factory
):
    from app.config import Settings

    monkeypatch.setattr(
        Settings,
        "provider_order",
        property(lambda self: {"maps": ["thunderforest", "osm_maps"]}),
    )
    chain = ExternalRegistry(
        http=mock_http_factory(_handler([]))
    ).chain_for("maps")

    assert [provider.name for provider in chain.providers] == [
        "thunderforest",
        "osm_maps",
    ]

    result = await chain.call("fetch", lat=_LAT, lon=_LON)

    assert result.provider_used == "thunderforest"
    assert result.value["source"] == "thunderforest"
    assert [attempt.outcome for attempt in result.attempts] == ["success"]
