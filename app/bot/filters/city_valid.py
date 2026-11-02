"""City input filter."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.utils.validators import is_valid_city_input


class CityValid(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.text and is_valid_city_input(message.text))