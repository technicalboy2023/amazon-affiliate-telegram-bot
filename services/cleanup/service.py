import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from database.models.duplicate import DuplicateCache
from database.models.message import ProcessedMessage
from database.models.stats import CleanupHistory, DailyStat

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def cleanup(self, *, user_id: int, stats_age_days: int = 30, keep_error_days: int = 30, duplicate_days: int = 30) -> dict:
        results = {"stats_deleted": 0, "errors_deleted": 0, "duplicates_deleted": 0, "vacuumed": False}
        cutoff = datetime.now(UTC) - timedelta(days=stats_age_days)
        error_cutoff = datetime.now(UTC) - timedelta(days=keep_error_days)
        dup_cutoff = datetime.now(UTC) - timedelta(days=duplicate_days)

        async with self.session_factory() as session:
            stmt = delete(DailyStat).where(
                DailyStat.user_id == user_id,
                DailyStat.date < cutoff.date(),
            )
            result = await session.execute(stmt)
            results["stats_deleted"] = result.rowcount

            stmt = delete(ProcessedMessage).where(
                ProcessedMessage.user_id == user_id,
                ProcessedMessage.status == "error",
                ProcessedMessage.processed_at < error_cutoff,
            )
            result = await session.execute(stmt)
            results["errors_deleted"] = result.rowcount

            stmt = delete(DuplicateCache).where(
                DuplicateCache.first_seen_at < dup_cutoff,
            )
            result = await session.execute(stmt)
            results["duplicates_deleted"] = result.rowcount

            session.add(CleanupHistory(
                user_id=user_id,
                tier2_rows_compacted=results["stats_deleted"],
                tier3_rows_deleted=results["errors_deleted"],
                notes=f"duplicates_cleared={results['duplicates_deleted']}",
            ))

            await session.commit()

        logger.info("Cleanup complete: %s", results)
        return results
