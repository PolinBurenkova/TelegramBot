"""Заглушка: geo_locations уже входит в baseline 0001.

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02

Ревизия оставлена пустой намеренно: вся схема описана в 0001 (см. докстринг
0001_initial.py), а цепочка 0002–0006 резервирует место под будущие изменения.
Правки схемы вносятся новой ревизией, а не редактированием применённых.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Ничего не делает: таблица geo_locations создана в 0001."""


def downgrade() -> None:
    """Ничего не делает: таблица geo_locations удаляется в downgrade 0001."""
