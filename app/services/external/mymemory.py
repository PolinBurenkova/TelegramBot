"""MyMemory — перевод текста. Ключ не нужен (суточный лимит по IP).

GET settings.mymemory_url/get?q=…&langpair=source|target
При source=auto в langpair уходит «Autodetect». Ответы-предупреждения
сервиса (лимит/пустой запрос) трактуются как None.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.external.base import BaseProvider

#: Служебные ответы сервиса вместо перевода.
_WARNING_PREFIXES = ("MYMEMORY WARNING", "QUERY LENGTH LIMIT", "PLEASE SELECT")


class MyMemoryProvider(BaseProvider):
    """translated.net/get: responseData.translatedText."""

    name = "mymemory"
    category = "translate"
    requires_key = False
    timeout = 15.0

    async def fetch(
        self, text: str, target: str = "ru", source: str = "auto", **kwargs: Any
    ) -> str | None:
        """Перевод текста или None."""
        if not text or not text.strip():
            return None
        base = get_settings().mymemory_url.rstrip("/")
        payload = await self.get_json(
            f"{base}/get",
            params={"q": text, "langpair": _langpair(target, source)},
        )
        return _translation(payload)


def _langpair(target: str, source: str) -> str:
    """langpair: «Autodetect|ru» при автоопределении."""
    target_lang = target.strip()
    if not source or source.strip().lower() == "auto":
        return f"Autodetect|{target_lang}"
    return f"{source.strip()}|{target_lang}"


def _translation(payload: Any) -> str | None:
    """translatedText при успешном responseStatus."""
    if not isinstance(payload, dict):
        return None
    status = payload.get("responseStatus")
    if status is not None and str(status) != "200":
        return None
    data = payload.get("responseData")
    data = data if isinstance(data, dict) else {}
    translated = data.get("translatedText")
    if not isinstance(translated, str) or not translated.strip():
        return None
    cleaned = translated.strip()
    if cleaned.upper().startswith(_WARNING_PREFIXES):
        return None
    return cleaned
