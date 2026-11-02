"""Страны: схема REST Countries и каскад «countries».

Все провайдеры цепочки стран работают без ключа, поэтому реестр собирает
полный список из ``PROVIDER_CHAINS["countries"]``. Отдельно проверяется
поведение пустой цепочки (все имена выпали из реестра) — детерминированный
``AllProvidersFailedError`` без попыток.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.constants import PROVIDER_CHAINS
from app.exceptions import AllProvidersFailedError
from app.schemas.api_responses import RestCountry
from app.services.external.registry import ExternalRegistry, build_chain

pytestmark = pytest.mark.external

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"


def _payload(case: str):
    return json.loads(
        (_MOCKS / "restcountries_responses.json").read_text(encoding="utf-8")
    )[case]


def test_rest_country_schema_parses_success_payload():
    country = RestCountry.model_validate(_payload("success")[0])

    assert country.name == {
        "common": "Russia",
        "official": "Russian Federation",
    }
    assert country.cca2 == "RU"
    assert country.capital == ["Moscow"]
    assert country.population == 144_104_080
    assert country.region == "Europe"
    assert country.flags == {
        "png": "https://example.test/flags/ru.png",
        "svg": "https://example.test/flags/ru.svg",
    }


def test_rest_country_schema_accepts_empty_list():
    assert [RestCountry.model_validate(item) for item in _payload("empty")] == []


def test_rest_country_schema_defaults_for_minimal_payload():
    country = RestCountry.model_validate({})

    assert country.name is None
    assert country.cca2 is None
    assert country.capital == []
    assert country.population is None
    assert country.region is None
    assert country.flags is None


def test_rest_country_schema_ignores_unknown_fields():
    country = RestCountry.model_validate(
        {"cca2": "RU", "borders": ["KZ"], "latlng": [60.0, 100.0]}
    )

    assert country.cca2 == "RU"
    assert not hasattr(country, "borders")


def test_countries_chain_lists_all_planned_providers():
    assert PROVIDER_CHAINS["countries"] == [
        "countries",
        "country_info",
        "flagcdn",
        "flagsapi",
        "country_state_city",
    ]


def test_registry_countries_chain_collects_all_providers():
    chain = ExternalRegistry().chain_for("countries")

    assert chain.name == "countries"
    assert [provider.name for provider in chain.providers] == PROVIDER_CHAINS["countries"]
    # В цепочке стран нет провайдеров с обязательным ключом, поэтому все они
    # готовы к работе без регистрации.
    assert all(provider.is_configured for provider in chain.providers)


async def test_countries_chain_call_fails_without_attempts():
    # Пустая цепочка (например, все имена выпали из реестра) детерминированно
    # падает с AllProvidersFailedError и нулевым списком попыток.
    chain = build_chain("countries", [])

    with pytest.raises(AllProvidersFailedError) as excinfo:
        await chain.call("fetch", country_code="RU")

    assert excinfo.value.chain_name == "countries"
    assert excinfo.value.attempts == []
    assert "игра продолжается" in excinfo.value.user_message


def test_build_chain_supports_empty_manual_chain():
    chain = build_chain("countries", [])

    assert chain.name == "countries"
    assert chain.providers == []
