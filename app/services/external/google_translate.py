"""Google Cloud Translation v2 — перевод текста. Ключ GOOGLE_TRANSLATE_API_KEY.

GET /language/translate/v2?q=…&target=…&format=text&key=…
source=auto означает автоопределение: параметр source тогда не отправляется.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

_API_URL = "https://translation.googleapis.com/language/translate/v2"


class GoogleTranslateProvider(BaseProvider):
    """v2 translate: data.translations[0].translatedText."""

    name = "google_translate"
    category = "translate"
    requires_key = True
    timeout = 15.0

    @property
    def api_key(self) -> str | None:
        """GOOGLE_TRANSLATE_API_KEY (Settings) или переменные окружения."""
        secret = get_settings().google_translate_api_key
        if secret:
            return secret.get_secret_value()
        return provider_key("google_translate")

    async def fetch(
        self, text: str, target: str = "ru", source: str = "auto", **kwargs: Any
    ) -> str | None:
        """Перевод текста или None."""
        key = self.api_key
        if not key:
            return None
        if not text or not text.strip():
            return None
        params: dict[str, Any] = {
            "q": text,
            "target": target,
            "format": "text",
            "key": key,
        }
        if source and source.strip().lower() != "auto":
            params["source"] = source
        payload = await self.get_json(_API_URL, params=params)
        return _translation(payload)


def _translation(payload: Any) -> str | None:
    """translatedText первого перевода."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    data = data if isinstance(data, dict) else {}
    items = data.get("translations")
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    if not isinstance(first, dict):
        return None
    translated = first.get("translatedText")
    if isinstance(translated, str) and translated.strip():
        return translated.strip()
    return None
