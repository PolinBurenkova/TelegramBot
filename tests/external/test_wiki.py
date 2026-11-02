"""Внешние провайдеры описаний и фото: Wikipedia REST и Wikimedia Commons."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest

from app.exceptions import ExternalAPIError, RateLimitError
from app.services.external.wiki import WikiProvider
from app.services.external.wikimedia import WikimediaProvider

pytestmark = pytest.mark.external

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
_WIKI_BASE = "https://wikipedia.test/api/rest_v1"
_COMMONS_BASE = "https://commons.test/w/api.php"


def _payload(name: str, case: str):
    return json.loads((_MOCKS / name).read_text(encoding="utf-8"))[case]


def _handler(payload, *, status: int = 200, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return handler


@pytest.fixture
def wiki_urls(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "wikipedia_base_url", _WIKI_BASE)
    monkeypatch.setattr(settings, "wikimedia_commons_base_url", _COMMONS_BASE)
    return settings


async def test_wiki_returns_stripped_extract(wiki_urls, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler({"extract": "  Москва — столица России.  \n"}, seen=seen)
    )
    provider = WikiProvider(http=client)

    result = await provider.fetch("Москва")

    assert result == "Москва — столица России."
    assert str(seen[0].url) == f"{_WIKI_BASE}/page/summary/{quote('Москва')}"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="no-extract"),
        pytest.param({"extract": "   "}, id="blank-extract"),
        pytest.param({"extract": None}, id="null-extract"),
    ],
)
async def test_wiki_returns_none_without_text(wiki_urls, mock_http_factory, payload):
    client = mock_http_factory(_handler(payload))
    provider = WikiProvider(http=client)

    assert await provider.fetch("Москва") is None


async def test_wiki_ignores_batch_query_shape(wiki_urls, mock_http_factory):
    """Мок ``wiki_responses.json`` собран под action=query, а не /page/summary."""
    client = mock_http_factory(_handler(_payload("wiki_responses.json", "success")))
    provider = WikiProvider(http=client)

    assert await provider.fetch("Москва") is None


async def test_wikimedia_returns_thumbnail(wiki_urls, mock_http_factory):
    seen: list[httpx.Request] = []
    client = mock_http_factory(
        _handler(_payload("wikimedia_responses.json", "success"), seen=seen)
    )
    provider = WikimediaProvider(http=client)

    result = await provider.fetch("Москва")

    assert result == "https://example.test/wikimedia/moscow_kremlin_1024.jpg"
    params = dict(seen[0].url.params)
    assert params["action"] == "query"
    assert params["format"] == "json"
    assert params["generator"] == "search"
    assert params["gsrsearch"] == "filetype:bitmap Москва"
    assert params["gsrlimit"] == "1"
    assert params["gsrnamespace"] == "6"
    assert params["prop"] == "imageinfo"
    assert params["iiprop"] == "url"
    assert params["iiurlwidth"] == "1024"
    assert seen[0].url.host == "commons.test"


async def test_wikimedia_falls_back_to_original_url(wiki_urls, mock_http_factory):
    payload = {
        "query": {
            "pages": {
                "1": {
                    "imageinfo": [
                        {"url": "https://example.test/wikimedia/original.jpg"}
                    ]
                }
            }
        }
    }
    client = mock_http_factory(_handler(payload))
    provider = WikimediaProvider(http=client)

    assert (
        await provider.fetch("Москва")
        == "https://example.test/wikimedia/original.jpg"
    )


async def test_wikimedia_returns_none_for_empty_pages(wiki_urls, mock_http_factory):
    client = mock_http_factory(_handler(_payload("wikimedia_responses.json", "empty")))
    provider = WikimediaProvider(http=client)

    assert await provider.fetch("Москва") is None


async def test_wikimedia_returns_none_without_query_block(
    wiki_urls, mock_http_factory
):
    client = mock_http_factory(_handler({"batchcomplete": ""}))
    provider = WikimediaProvider(http=client)

    assert await provider.fetch("Москва") is None


@pytest.mark.parametrize(
    ("status", "expected", "reason"),
    [
        pytest.param(429, RateLimitError, "rate limited", id="rate-limited"),
        pytest.param(500, ExternalAPIError, "HTTP 500", id="server-error"),
    ],
)
async def test_wikimedia_maps_http_errors(
    wiki_urls, mock_http_factory, status, expected, reason
):
    client = mock_http_factory(_handler({}, status=status))
    provider = WikimediaProvider(http=client)

    with pytest.raises(expected) as excinfo:
        await provider.fetch("Москва")

    assert excinfo.value.provider == "wikimedia"
    assert reason in excinfo.value.message
