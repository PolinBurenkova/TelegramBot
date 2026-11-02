"""Вспомогательные функции GeoGuessr."""


def format_distance(km: float) -> str:
    if km < 1:
        return f"{int(km * 1000)} м"
    return f"{km:.1f} км"