"""Проверка корректности хода в «Городах»."""

from app.constants import CITY_MIN_LENGTH
from app.exceptions import CityAlreadyUsed, InvalidCity, WrongLetter
from app.utils.validators import is_valid_city_name
from app.utils.validators import last_letter as _last_letter


def last_letter(city: str) -> str:
    """Последняя значимая буква города.

    Делегирует в общий :func:`app.utils.validators.last_letter`, чтобы правило
    было единым: отбрасываются только «немые» ь/ъ/ы, «й» остаётся рабочей
    буквой («Волжский» → следующий на «й»), «ё» приводится к «е».
    """
    return _last_letter(city)


def validate_city(
    city: str,
    required_letter: str | None,
    used_cities: set[str],
) -> str:
    """Проверяет город и возвращает нормализованное имя."""
    cleaned = city.strip()
    if not is_valid_city_name(cleaned) or len(cleaned) < CITY_MIN_LENGTH:
        raise InvalidCity(f"Некорректное название: {city!r}")
    if required_letter and cleaned[0].lower() != required_letter.lower():
        raise WrongLetter(
            f"Город должен начинаться на «{required_letter.upper()}»"
        )
    if cleaned.lower() in used_cities:
        raise CityAlreadyUsed(f"Город «{cleaned}» уже был")
    return cleaned
