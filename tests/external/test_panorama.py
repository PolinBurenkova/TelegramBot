"""Внешние провайдеры панорам: Mapillary (токен) и KartaView (без ключа)."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.kartaview import KartaViewProvider
from app.services.external.mapillary import MapillaryProvider
from app.utils.provider_chain import ProviderChain

pytestmark = pytest.mark.external

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
_KARTAVIEW_BASE = "https://kartaview.test/2.0"

_LAT = 55.7558
_LON = 37.6173


def _payload(name: str, case: str):
    return json.loads((_MOCKS / name).read_text(encoding="utf-8"))[case]


def _handler(payload, *, status: int = 200, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return handler


@pytest.fixture
def panorama_settings(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "kartaview_base_url", _KARTAVIEW_BASE)
    monkeypatch.setattr(settings, "mapillary_token", SecretStr("mly-key"))
    return settings


async def test_kartaview_returns_panorama_url(panorama_settings, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("kartaview_responses.json", "success"), seen=seen)
    )
    provider = KartaViewProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result == {
        "image_url": "https://example.test/kartaview/111_thumb.jpg",
        "lat": _LAT,
        "lon": _LON,
        "source": "kartaview",
    }
    request = seen[0]
    assert request.url.path.endswith("/photo/")
    params = dict(request.url.params)
    assert params["clat"] == "55.7558"
    assert params["clng"] == "37.6173"
    assert params["radius"] == "0.02"
    assert params["page"] == "1"
    assert params["ipp"] == "1"


async def test_kartaview_returns_none_for_empty_page(
    panorama_settings, mock_http_factory
):
    client = mock_http_factory(_handler(_payload("kartaview_responses.json", "empty")))
    provider = KartaViewProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


async def test_kartaview_supports_legacy_result_envelope(
    panorama_settings, mock_http_factory
):
    client = mock_http_factory(
        _handler(_payload("kartaview_responses.json", "success_result"))
    )
    provider = KartaViewProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result is not None
    assert result["image_url"] == "https://example.test/kartaview/222_thumb.jpg"
    assert result["source"] == "kartaview"


async def test_kartaview_falls_back_to_full_size_url(
    panorama_settings, mock_http_factory
):
    payload = {
        "currentPageItems": [{"url": "https://example.test/kartaview/333.jpg"}]
    }
    client = mock_http_factory(_handler(payload))
    provider = KartaViewProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result is not None
    assert result["image_url"] == "https://example.test/kartaview/333.jpg"


async def test_mapillary_returns_none_without_token(monkeypatch, mock_http_factory):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "mapillary_token", None)
    seen: list[httpx.Request] = []
    client = mock_http_factory(_handler({}, seen=seen))
    provider = MapillaryProvider(http=client)

    assert provider.is_configured is False
    assert await provider.fetch(_LAT, _LON) is None
    assert seen == []


async def test_mapillary_returns_thumbnail(panorama_settings, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("mapillary_responses.json", "success"), seen=seen)
    )
    provider = MapillaryProvider(http=client)

    result = await provider.fetch(_LAT, _LON)

    assert result == {
        "image_url": (
            "https://example.test/mapillary/123456789012345_1024.jpg"
        ),
        "lat": _LAT,
        "lon": _LON,
        "source": "mapillary",
    }
    params = dict(seen[0].url.params)
    assert params["access_token"] == "mly-key"
    bbox = [float(part) for part in params["bbox"].split(",")]
    assert bbox == pytest.approx([37.5973, 55.7458, 37.6373, 55.7658])
    assert params["fields"] == "thumb_1024_url,geometry"
    assert params["limit"] == "1"
    assert seen[0].url.host == "graph.mapillary.com"


async def test_mapillary_returns_none_for_empty_data(
    panorama_settings, mock_http_factory
):
    client = mock_http_factory(_handler(_payload("mapillary_responses.json", "empty")))
    provider = MapillaryProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


async def test_mapillary_returns_none_for_error_envelope(
    panorama_settings, mock_http_factory
):
    client = mock_http_factory(_handler(_payload("mapillary_responses.json", "error")))
    provider = MapillaryProvider(http=client)

    assert await provider.fetch(_LAT, _LON) is None


@pytest.mark.parametrize(
    ("status", "expected", "reason"),
    [
        pytest.param(429, RateLimitError, "rate limited", id="rate-limited"),
        pytest.param(500, ExternalAPIError, "HTTP 500", id="server-error"),
    ],
)
async def test_mapillary_maps_http_errors(
    panorama_settings, mock_http_factory, status, expected, reason
):
    client = mock_http_factory(_handler({}, status=status))
    provider = MapillaryProvider(http=client)

    with pytest.raises(expected) as excinfo:
        await provider.fetch(_LAT, _LON)

    assert excinfo.value.provider == "mapillary"
    assert reason in excinfo.value.message


async def test_panorama_chain_skips_unconfigured_mapillary(
    monkeypatch, panorama_settings, mock_http_factory, fake_redis
):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "mapillary_token", None)
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("kartaview_responses.json", "success"), seen=seen)
    )
    chain = ProviderChain(
        "panorama",
        [MapillaryProvider(http=client), KartaViewProvider(http=client)],
        redis=fake_redis,
    )

    result = await chain.call("fetch", lat=_LAT, lon=_LON)

    assert result.provider_used == "kartaview"
    assert result.value["source"] == "kartaview"
    assert [(a.provider, a.outcome) for a in result.attempts] == [
        ("mapillary", "skipped"),
        ("kartaview", "success"),
    ]
    assert result.attempts[0].reason == "not_configured"
    assert len(seen) == 1
