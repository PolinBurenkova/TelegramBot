"""DeepL — перевод текста. Ключ DEEPL_API_KEY.

Free-ключи DeepL оканчиваются на «:fx» и работают только с api-free.deepl.com,
ключи Pro — с api.deepl.com; endpoint выбирается по суффиксу ключа.
source=auto означает автоопределение: source_lang тогда не отправляется.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider, provider_key

_FREE_URL = "https://api-free.deepl.com/v2/translate"
_PRO_URL = "https://api.deepl.com/v2/translate"


class DeepLProvider(BaseProvider):
    """v2/translate: translations[0].text."""

    name = "deepl"
    category = "translate"
    requires_key = True
    timeout = 15.0

    @property
    def api_key(self) -> str | None:
        """DEEPL_API_KEY (Settings) или переменные окружения."""
        secret = get_settings().deepl_api_key
        if secret:
            return secret.get_secret_value()
        return provider_key("deepl")

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
            "auth_key": key,
            "text": text,
            "target_lang": target.strip().upper(),
        }
        if source and source.strip().lower() != "auto":
            params["source_lang"] = source.strip().upper()
        payload = await self.get_json(_endpoint(key), params=params)
        return _translation(payload)


def _endpoint(key: str) -> str:
    """Free-ключи (суффикс :fx) обслуживает api-free.deepl.com."""
    return _FREE_URL if key.endswith(":fx") else _PRO_URL


def _translation(payload: Any) -> str | None:
    """text первого перевода."""
    if not isinstance(payload, dict):
        return None
    items = payload.get("translations")
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    if not isinstance(first, dict):
        return None
    translated = first.get("text")
    if isinstance(translated, str) and translated.strip():
        return translated.strip()
    return None
