# tests/unit/test_geo_utils.py
"""Юнит-тесты гео-хелперов (`app/utils/geo.py`)."""

from __future__ import annotations

import pytest

from app.utils.geo import format_coordinates, format_distance, haversine_km

MOSCOW = (55.7558, 37.6173)
SAINT_PETERSBURG = (59.9343, 30.3351)


def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(*MOSCOW, *MOSCOW) == pytest.approx(0.0, abs=1e-9)


def test_haversine_moscow_to_saint_petersburg() -> None:
    distance = haversine_km(*MOSCOW, *SAINT_PETERSBURG)

    assert distance == pytest.approx(634.0, abs=5.0)


def test_haversine_is_symmetric() -> None:
    forward = haversine_km(*MOSCOW, *SAINT_PETERSBURG)
    backward = haversine_km(*SAINT_PETERSBURG, *MOSCOW)

    assert forward == pytest.approx(backward, abs=1e-9)


@pytest.mark.parametrize(
    ("km", "expected"),
    [
        (0.0, "0 м"),
        (0.5, "500 м"),
        (0.999, "999 м"),
        (1.0, "1.0 км"),
        (12.34, "12.3 км"),
        (99.0, "99.0 км"),
        (150.7, "150 км"),
        (634.1234, "634 км"),
    ],
    ids=["zero", "500m", "999m", "1km", "12km", "99km", "150km", "634km"],
)
def test_format_distance(km: float, expected: str) -> None:
    assert format_distance(km) == expected


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (55.7558, 37.6173, "55.7558, 37.6173"),
        (-33.8688, 151.2093, "-33.8688, 151.2093"),
        (0.0, 0.0, "0.0000, 0.0000"),
    ],
    ids=["moscow", "sydney", "null-island"],
)
def test_format_coordinates(lat: float, lon: float, expected: str) -> None:
    assert format_coordinates(lat, lon) == expected
