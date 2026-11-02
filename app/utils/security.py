"""Security helpers."""
from __future__ import annotations

import hashlib

from app.config import get_settings


def is_safe_text(text: str, max_len: int = 4096) -> bool:
    return 0 < len(text) <= max_len and "\x00" not in text


def is_admin(tg_id: int) -> bool:
    return tg_id in get_settings().admin.ids


def hash_key(key: str) -> str:
    """Hash cache keys with sensitive params."""
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def escape_user_input(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")