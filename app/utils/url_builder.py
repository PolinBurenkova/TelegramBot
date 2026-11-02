"""URL builder."""

from urllib.parse import urlencode


def build_url(base: str, params: dict) -> str:
    return f"{base}?{urlencode(params)}"