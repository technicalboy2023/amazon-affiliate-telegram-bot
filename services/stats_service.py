import logging
from datetime import UTC, date, datetime

from sqlalchemy import select

from database.models.stats import DailyStat

logger = logging.getLogger(__name__)


class StatsService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def record_publish(self, user_id: int, pipeline_id: int, status: str = "success") -> None:
        today = date.today()
        async with self.session_factory() as session:
            stmt = select(DailyStat).where(
                DailyStat.user_id == user_id,
                DailyStat.date == today,
            )
            result = await session.execute(stmt)
            stat = result.scalar_one_or_none()
            if stat is None:
                stat = DailyStat(user_id=user_id, date=today)
                session.add(stat)
            stat.messages_processed = (stat.messages_processed or 0) + 1
            if status == "success":
                stat.messages_published = (stat.messages_published or 0) + 1
            else:
                stat.errors_count = (stat.errors_count or 0) + 1
            stat.last_activity = datetime.now(UTC)
            await session.commit()

    async def get_today_stats(self, user_id: int) -> dict:
        today = date.today()
        async with self.session_factory() as session:
            stmt = select(DailyStat).where(
                DailyStat.user_id == user_id,
                DailyStat.date == today,
            )
            result = await session.execute(stmt)
            stat = result.scalar_one_or_none()
            if stat is None:
                return {"processed": 0, "published": 0, "errors": 0}
            return {
                "processed": stat.messages_processed or 0,
                "published": stat.messages_published or 0,
                "errors": stat.errors_count or 0,
            }
