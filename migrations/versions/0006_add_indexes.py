"""Заглушка: daily_challenges, notifications и индексы уже входят в baseline 0001.

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-06

См. докстринг 0001_initial.py.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Ничего не делает: таблицы и индексы созданы в 0001."""


def downgrade() -> None:
    """Ничего не делает: таблицы и индексы удаляются в downgrade 0001."""
