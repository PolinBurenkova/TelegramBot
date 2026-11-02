"""HTTP-клиент на httpx.

Единый AsyncClient для всех провайдеров. Не создавать новый на каждый запрос.
"""

from typing import Any

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
DEFAULT_HEADERS = {
    "User-Agent": "CitiesPlusBot/1.0 (+https://github.com/)",
    "Accept": "application/json",
}


def create_client(
    *,
    base_url: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Создаёт AsyncClient с настройками по умолчанию."""
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    return httpx.AsyncClient(
        base_url=base_url or "",
        headers=merged_headers,
        timeout=timeout,
        follow_redirects=True,
        **kwargs,
    )


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET-запрос и возврат JSON. Поднимает httpx.HTTPError."""
    response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


# ─── Общая сессия на всё приложение ─────────────────────────────────────────
# Провайдеры без injected-клиента используют этот синглтон;
# диспетчер кладёт его же в dp["http_session"] при старте.

_shared_client: httpx.AsyncClient | None = None


def create_http_session() -> httpx.AsyncClient:
    """Вернуть общий AsyncClient (создаётся лениво)."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = create_client()
    return _shared_client


async def close_http_session() -> None:
    """Закрыть общую HTTP-сессию (вызывается при остановке бота)."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None