"""Рендер статической карты с 2 точками."""

from urllib.parse import urlencode

from app.config import settings


def build_static_map_url(
    real_lat: float,
    real_lon: float,
    guess_lat: float,
    guess_lon: float,
    width: int = 600,
    height: int = 400,
) -> str:
    """Ссылка на статическую карту OSM с 2 маркерами."""
    base = f"{settings.osm_static_base_url}/staticmap.php"
    params = {
        "center": f"{(real_lat + guess_lat) / 2},{(real_lon + guess_lon) / 2}",
        "zoom": 3,
        "size": f"{width}x{height}",
        "maptype": "mapnik",
        "markers": f"{real_lat},{real_lon},red-pushpin|{guess_lat},{guess_lon},blue-pushpin",
    }
    return f"{base}?{urlencode(params)}"