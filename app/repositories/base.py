""""Generic base repository."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import RepositoryError
from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepo(Generic[ModelT]):
    """Base CRUD operations for a SQLAlchemy model."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        """Get by primary key."""
        try:
            return await self.session.get(self.model, id_)
        except Exception as e:
            raise RepositoryError(f"get({id_}) failed: {e}") from e

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """List with pagination."""
        res = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(res.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        """Insert new row."""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: ModelT, **fields: Any) -> ModelT:
        """Update fields on instance."""
        for k, v in fields.items():
            setattr(obj, k, v)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Delete instance."""
        await self.session.delete(obj)
        await self.session.flush()

    async def count(self) -> int:
        """Count rows."""
        res = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return int(res.scalar_one())


# Совместимость: move_repo и user_achievement_repo импортируют BaseRepository
BaseRepository = BaseRepo