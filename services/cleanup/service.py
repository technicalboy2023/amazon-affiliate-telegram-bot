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

    async def cleanup(self, *, user_id: int = 1, stats_age_days: int = 7, log_retention_days: int = 7, duplicate_days: int = 7, history_retention_days: int = 7) -> dict:
        results = {"logs_deleted": 0, "duplicates_deleted": 0, "stats_deleted": 0, "history_deleted": 0}
        log_cutoff = datetime.now(UTC) - timedelta(days=log_retention_days)
        dup_cutoff = datetime.now(UTC) - timedelta(days=duplicate_days)
        stats_cutoff = datetime.now(UTC) - timedelta(days=stats_age_days)
        history_cutoff = datetime.now(UTC) - timedelta(days=history_retention_days)

        async with self.session_factory() as session:
            stmt = delete(ProcessedMessage).where(
                ProcessedMessage.user_id == user_id,
                ProcessedMessage.processed_at < log_cutoff,
            )
            result = await session.execute(stmt)
            results["logs_deleted"] = result.rowcount

            stmt = delete(DuplicateCache).where(
                DuplicateCache.first_seen_at < dup_cutoff,
            )
            result = await session.execute(stmt)
            results["duplicates_deleted"] = result.rowcount

            stmt = delete(DailyStat).where(
                DailyStat.user_id == user_id,
                DailyStat.date < stats_cutoff.date(),
            )
            result = await session.execute(stmt)
            results["stats_deleted"] = result.rowcount

            stmt = delete(CleanupHistory).where(
                CleanupHistory.started_at < history_cutoff,
            )
            result = await session.execute(stmt)
            results["history_deleted"] = result.rowcount

            session.add(CleanupHistory(
                user_id=user_id,
                tier2_rows_compacted=results["stats_deleted"],
                tier3_rows_deleted=results["logs_deleted"],
                notes=f"duplicates={results['duplicates_deleted']} history={results['history_deleted']}",
            ))

            await session.commit()

        logger.info("Cleanup complete: %s", results)
        return results
