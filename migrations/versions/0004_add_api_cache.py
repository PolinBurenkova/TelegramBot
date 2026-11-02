"""Заглушка: api_cache уже входит в baseline 0001.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04

См. докстринг 0001_initial.py.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Ничего не делает: таблица api_cache создана в 0001."""


def downgrade() -> None:
    """Ничего не делает: таблица api_cache удаляется в downgrade 0001."""
