"""
Async SQLAlchemy engine and session factory.

Configures SQLite with aiosqlite for async operations.
Database-agnostic: change DATABASE_URL to switch to PostgreSQL.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.models.base import Base

logger = logging.getLogger(__name__)


def _set_sqlite_pragmas(dbapi_conn, connection_record):
    """Set SQLite performance pragmas on every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-8000")  # 8MB cache
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_engine(database_url: str):
    """Create async SQLAlchemy engine."""
    # Ensure SQLite directory exists
    if "sqlite" in database_url:
        db_path = database_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Apply SQLite-specific optimizations
    if "sqlite" in database_url:
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)

    logger.info("Database engine created: %s", database_url.split("///")[0] + "///***")
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
