import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.exc import IntegrityError

from database.models.duplicate import DuplicateCache

logger = logging.getLogger(__name__)


class DuplicateChecker:
    def __init__(self, session_factory, window_hours: int = 720):
        self.session_factory = session_factory
        self.window_hours = window_hours

    async def is_duplicate(self, asin: str, pipeline_id: int) -> bool:
        cutoff = datetime.now(UTC) - timedelta(hours=self.window_hours)
        async with self.session_factory() as session:
            stmt = select(DuplicateCache).where(
                DuplicateCache.asin == asin,
                DuplicateCache.pipeline_id == pipeline_id,
                DuplicateCache.first_seen_at >= cutoff,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def mark_seen(self, asin: str, pipeline_id: int, source_channel_id: int, source_message_id: int | None = None, user_id: int | None = None) -> None:
        from config.settings import get_settings
        uid = user_id if user_id is not None else get_settings().default_user_id
        async with self.session_factory() as session:
            try:
                session.add(DuplicateCache(
                    user_id=uid,
                    pipeline_id=pipeline_id,
                    asin=asin,
                    source_channel_id=source_channel_id,
                    source_message_id=source_message_id,
                ))
                await session.commit()
            except IntegrityError:
                await session.rollback()
                await session.execute(
                    sql_update(DuplicateCache)
                    .where(DuplicateCache.pipeline_id == pipeline_id, DuplicateCache.asin == asin)
                    .values(first_seen_at=datetime.now(UTC))
                )
                await session.commit()
