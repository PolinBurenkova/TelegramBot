"""Базовые схемы ответов."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Базовая pydantic-схема проекта."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class OkResponse(BaseSchema):
    """Стандартный ответ «ОК»."""

    ok: bool = True


class Pagination(BaseSchema):
    """Пагинация."""

    page: int = 0
    size: int = 10
    total: int = 0


class Page(BaseSchema, Generic[T]):
    """Страница результатов."""

    items: list[T] = []
    pagination: Pagination = Pagination()
