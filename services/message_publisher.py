import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from telethon import TelegramClient

from database.models.message import ProcessedMessage
from database.repositories.message_repo import MessageRepository

logger = logging.getLogger(__name__)


class MessagePublisher:
    def __init__(self, userbot: TelegramClient, session_factory: async_sessionmaker):
        self.userbot = userbot
        self.session_factory = session_factory

    async def is_already_processed(self, source_channel_id: int, source_message_id: int) -> bool:
        async with self.session_factory() as session:
            stmt = select(ProcessedMessage).where(
                ProcessedMessage.source_channel_id == source_channel_id,
                ProcessedMessage.source_message_id == source_message_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def publish(self, *, source_channel_id: int, source_message_id: int, dest_channel: int | str, text: str, original_text: str, asins: list[str], links_replaced: int, user_id: int, pipeline_id: int, had_media: bool = False, media_type: str | None = None, media_obj: object | None = None) -> int | None:
        try:
            entity = await self.userbot.get_entity(dest_channel)
            if had_media and media_obj is not None:
                msg = await self.userbot.send_file(entity, media_obj, caption=text)
            else:
                msg = await self.userbot.send_message(entity, text)
            dest_message_id = msg.id
            dest_channel_id = entity.id if hasattr(entity, "id") else dest_channel
        except Exception as e:
            logger.error("Failed to publish to %s: %s", dest_channel, e)
            async with self.session_factory() as session:
                repo = MessageRepository(session)
                await repo.log_processed(
                    user_id=user_id,
                    pipeline_id=pipeline_id,
                    source_channel_id=source_channel_id,
                    source_message_id=source_message_id,
                    original_text=original_text,
                    modified_text=text,
                    asins_found=str(asins),
                    links_replaced=links_replaced,
                    had_media=had_media,
                    media_type=media_type,
                    status="error",
                    error_message=str(e),
                )
                await session.commit()
            return None

        async with self.session_factory() as session:
            repo = MessageRepository(session)
            await repo.log_processed(
                user_id=user_id,
                pipeline_id=pipeline_id,
                source_channel_id=source_channel_id,
                source_message_id=source_message_id,
                dest_channel_id=dest_channel_id,
                dest_message_id=dest_message_id,
                original_text=original_text,
                modified_text=text,
                asins_found=str(asins),
                links_replaced=links_replaced,
                had_media=had_media,
                media_type=media_type,
                status="success",
            )
            await session.commit()

        logger.info("Published msg %d->%d to %s (asins=%s)", source_message_id, dest_message_id, dest_channel, asins)
        return dest_message_id
