"""FlagsAPI — PNG-флаг страны по ISO2. Ключ не нужен.

Проверено по документации сервиса: путь https://flagsapi.com/{CC}/flat/64.png
отдаётся без ключа (ключ нужен только для повышенных лимитов, здесь не
используется). URL детерминирован, HTTP-запрос не выполняется.
SVG FlagsAPI не отдаёт, поэтому flag_svg = None.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider


class FlagsAPIProvider(BaseProvider):
    """Ссылки на флаг: png 64px flat и эмодзи из ISO2."""

    name = "flagsapi"
    category = "countries"
    requires_key = False

    async def fetch(self, country_code: str, **kwargs: Any) -> dict[str, Any] | None:
        """Флаг страны или None для некорректного кода."""
        code = _normalize_code(country_code)
        if code is None:
            return None
        base = get_settings().flagsapi_base_url.rstrip("/")
        return {
            "code": code,
            "flag_url": f"{base}/{code}/flat/64.png",
            "flag_svg": None,
            "emoji": _emoji(code),
            "source": "flagsapi",
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
