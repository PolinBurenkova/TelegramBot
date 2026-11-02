"""JSON-based i18n with fallback to DEFAULT_LOCALE."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = "ru"


@lru_cache(maxsize=10)
def load_locale(locale: str) -> dict[str, str]:
    """Load locale JSON."""
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / f"{DEFAULT_LOCALE}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class Translator:
    """Translator with placeholder formatting."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        self.locale = locale if locale in ("ru", "en") else DEFAULT_LOCALE
        self._data = load_locale(self.locale)
        self._fallback = load_locale(DEFAULT_LOCALE)

    def t(self, key: str, **kwargs: object) -> str:
        """Translate key with fallback."""
        text = self._data.get(key) or self._fallback.get(key) or key
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text


def translator(locale: str) -> Translator:
    """Factory."""
    return Translator(locale)