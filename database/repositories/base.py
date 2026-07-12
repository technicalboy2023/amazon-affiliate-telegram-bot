"""
Generic async CRUD repository.

All specific repositories inherit from this base.
Provides standard operations: get, list, create, update, delete.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.base import Base

T = TypeVar("T", bound=Base)
logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """
    Generic async repository providing CRUD operations.

    Usage:
        class UserRepo(BaseRepository[User]):
            model = User
    """

    model: type[T]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> T | None:
        """Get a single record by primary key."""
        return await self.session.get(self.model, id)

    async def get_one(self, **filters: Any) -> T | None:
        """Get a single record by arbitrary filters."""
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> Sequence[T]:
        """Get all records with optional filtering and pagination."""
        stmt = select(self.model).filter_by(**filters).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        """Count records with optional filtering."""
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **data: Any) -> T:
        """Create a new record."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update_by_id(self, id: int, **data: Any) -> T | None:
        """Update a record by primary key."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete_by_id(self, id: int) -> bool:
        """Delete a record by primary key."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def bulk_delete(self, **filters: Any) -> int:
        """Delete multiple records by filter. Returns count deleted."""
        stmt = sa_delete(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def exists(self, **filters: Any) -> bool:
        """Check if a record exists."""
        stmt = select(func.count()).select_from(self.model).filter_by(**filters).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
