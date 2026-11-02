# tests/unit/test_geo_score.py
"""Скоринг GeoGuessr: haversine и экспоненциальное затухание очков."""

import pytest

from app.constants import GEO_MAX_SCORE
from app.services.geo_score import calculate_score, haversine


def test_haversine_zero_distance() -> None:
    assert haversine(55.75, 37.61, 55.75, 37.61) == pytest.approx(0.0, abs=1e-9)


def test_haversine_moscow_to_spb() -> None:
    # Москва → Санкт-Петербург ≈ 635 км
    distance = haversine(55.7558, 37.6173, 59.9343, 30.3351)
    assert 620 < distance < 650


def test_haversine_is_symmetric() -> None:
    a = haversine(10.0, 20.0, -30.0, 40.0)
    b = haversine(-30.0, 40.0, 10.0, 20.0)
    assert a == pytest.approx(b)


def test_score_is_max_at_zero_distance() -> None:
    assert calculate_score(0.0) == GEO_MAX_SCORE


def test_score_decays_monotonically() -> None:
    scores = [calculate_score(km) for km in (0.0, 100.0, 1_000.0, 5_000.0)]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > scores[-1]


def test_score_never_negative() -> None:
    assert calculate_score(100_000.0) >= 0
