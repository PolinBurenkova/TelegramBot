"""Заглушка: achievements и user_achievements уже входят в baseline 0001.

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-03

См. докстринг 0001_initial.py: схемa целиком описана в 0001, эта ревизия
резервирует цепочку для будущих изменений.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Ничего не делает: таблицы созданы в 0001."""


def downgrade() -> None:
    """Ничего не делает: таблицы удаляются в downgrade 0001."""
