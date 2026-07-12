"""
Message repository for processed message logs.
"""

from __future__ import annotations

from sqlalchemy import select

from database.models.message import ProcessedMessage
from database.repositories.base import BaseRepository


class MessageRepository(BaseRepository[ProcessedMessage]):
    model = ProcessedMessage

    async def is_already_processed(
        self, user_id: int, pipeline_id: int, source_channel_id: int, source_message_id: int
    ) -> bool:
        """Check if a message was already processed."""
        return await self.exists(
            user_id=user_id,
            pipeline_id=pipeline_id,
            source_channel_id=source_channel_id,
            source_message_id=source_message_id,
        )

    async def log_processed(
        self,
        user_id: int,
        pipeline_id: int,
        source_channel_id: int,
        source_message_id: int,
        dest_channel_id: int | None = None,
        dest_message_id: int | None = None,
        original_text: str | None = None,
        modified_text: str | None = None,
        asins_found: str | None = None,
        links_replaced: int = 0,
        had_media: bool = False,
        media_type: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> ProcessedMessage:
        """Log a processed message."""
        return await self.create(
            user_id=user_id,
            pipeline_id=pipeline_id,
            source_channel_id=source_channel_id,
            source_message_id=source_message_id,
            dest_channel_id=dest_channel_id,
            dest_message_id=dest_message_id,
            original_text=original_text,
            modified_text=modified_text,
            asins_found=asins_found,
            links_replaced=links_replaced,
            had_media=had_media,
            media_type=media_type,
            status=status,
            error_message=error_message,
        )

    async def get_recent(self, user_id: int, limit: int = 20) -> list[ProcessedMessage]:
        """Get recent processed messages."""
        stmt = (
            select(ProcessedMessage)
            .where(ProcessedMessage.user_id == user_id)
            .order_by(ProcessedMessage.processed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_error_messages(self, user_id: int, limit: int = 20) -> list[ProcessedMessage]:
        """Get recent error messages."""
        stmt = (
            select(ProcessedMessage)
            .where(ProcessedMessage.user_id == user_id, ProcessedMessage.status == "error")
            .order_by(ProcessedMessage.processed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
