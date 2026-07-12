"""
Async SQLAlchemy engine and session factory.

PostgreSQL via asyncpg. Set DATABASE_URL in .env.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.models.base import Base

logger = logging.getLogger(__name__)


def create_engine(database_url: str):
    """Create async SQLAlchemy engine."""
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    logger.info("Database engine created")
    return engine


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def init_db(engine) -> None:
    """Create all tables. Used for initial setup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")
