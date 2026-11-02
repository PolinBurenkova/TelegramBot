"""Заглушка: user_used_cities уже входит в baseline 0001.

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-05

См. докстринг 0001_initial.py.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Ничего не делает: таблица user_used_cities создана в 0001."""


def downgrade() -> None:
    """Ничего не делает: таблица user_used_cities удаляется в downgrade 0001."""
