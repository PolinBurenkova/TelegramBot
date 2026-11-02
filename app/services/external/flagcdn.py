"""FlagCDN — URL флага страны по ISO2. Ключ не нужен.

URL детерминированы (https://flagcdn.com/w320/{cc}.png и /{cc}.svg),
поэтому HTTP-запрос не выполняется — только сборка ссылок и эмодзи.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class FlagCDNProvider(BaseProvider):
    """Ссылки на флаг: png 320px, svg и эмодзи из ISO2."""

    name = "flagcdn"
    category = "countries"
    requires_key = False

    async def fetch(self, country_code: str, **kwargs: Any) -> dict[str, Any] | None:
        """Флаг страны или None для некорректного кода."""
        code = _normalize_code(country_code)
        if code is None:
            return None
        lower = code.lower()
        base = get_settings().flagcdn_base_url.rstrip("/")
        return {
            "code": code,
            "flag_url": f"{base}/w320/{lower}.png",
            "flag_svg": f"{base}/{lower}.svg",
            "emoji": _emoji(code),
            "source": "flagcdn",
        }


def _normalize_code(value: Any) -> str | None:
    """ISO2: ровно две латинские буквы, иначе None."""
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        return None
    return code


def _emoji(code: str) -> str:
    """ISO2 → эмодзи флага (региональные индикаторы)."""
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in code)
