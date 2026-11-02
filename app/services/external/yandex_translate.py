"""Yandex Translate (v1.5) — перевод текста. Ключ YANDEX_TRANSLATE_API_KEY.

GET /api/v1.5/tr.json/translate?key=…&text=…&lang=ru&format=plain
При source=auto в lang передаётся только целевой язык (автоопределение),
иначе пара «source-target».
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

_API_URL = "https://translate.yandex.net/api/v1.5/tr.json/translate"


class YandexTranslateProvider(BaseProvider):
    """tr.json/translate: text[0] при code == 200."""

    name = "yandex_translate"
    category = "translate"
    requires_key = True
    timeout = 15.0

    @property
    def api_key(self) -> str | None:
        """YANDEX_TRANSLATE_API_KEY (Settings) или переменные окружения."""
        secret = get_settings().yandex_translate_api_key
        if secret:
            return secret.get_secret_value()
        return provider_key("yandex_translate")

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
            "key": key,
            "text": text,
            "format": "plain",
            "lang": _lang(target, source),
        }
        payload = await self.get_json(_API_URL, params=params)
        return _translation(payload)


def _lang(target: str, source: str) -> str:
    """lang для API: «ru» при автоопределении, иначе «en-ru»."""
    target_lang = target.strip().lower()
    if not source or source.strip().lower() == "auto":
        return target_lang
    return f"{source.strip().lower()}-{target_lang}"


def _translation(payload: Any) -> str | None:
    """text[0] успешного ответа."""
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    if isinstance(code, int) and code != 200:
        return None
    texts = payload.get("text")
    if not isinstance(texts, list) or not texts:
        return None
    first = texts[0]
    if isinstance(first, str) and first.strip():
        return first.strip()
    return None
