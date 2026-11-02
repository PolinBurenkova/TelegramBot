"""LibreTranslate provider."""

from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.services.external.base import BaseProvider


class LibreTranslateProvider(BaseProvider):
    name = "libretranslate"
    category = "translate"

    async def call(self, method: str, **kwargs: Any) -> Any:
        if method == "translate":
            return await self._translate(
                kwargs["text"], kwargs.get("source", "auto"), kwargs["target"]
            )
        return None

    async def _translate(self, text: str, source: str, target: str) -> str | None:
        payload = {"q": text, "source": source, "target": target, "format": "text"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{settings.libretranslate_url}/translate", json=payload
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(f"LibreTranslate error: {exc}")
            return None
        return data.get("translatedText")