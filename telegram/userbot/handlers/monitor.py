import asyncio
import logging

from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto, MessageMediaWebPage

from config.settings import Settings
from services.post_customizer import PostCustomizer
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)

MEDIA_PHOTO = "photo"
MEDIA_VIDEO = "video"
MEDIA_DOCUMENT = "document"
MEDIA_GIF = "gif"
MEDIA_AUDIO = "audio"
MEDIA_UNKNOWN = "unknown"


def _detect_media(event: NewMessage.Event) -> tuple[bool, str | None, object | None]:
    media = event.message.media
    if media is None:
        return False, None, None

    if isinstance(media, MessageMediaPhoto):
        return True, MEDIA_PHOTO, media
    if isinstance(media, MessageMediaDocument):
        doc_attrs = {a.__class__.__name__ for a in media.document.attributes} if media.document else set()
        if "DocumentAttributeVideo" in doc_attrs:
            return True, MEDIA_VIDEO, media
        if "DocumentAttributeAnimated" in doc_attrs:
            return True, MEDIA_GIF, media
        if "DocumentAttributeAudio" in doc_attrs:
            return True, MEDIA_AUDIO, media
        return True, MEDIA_DOCUMENT, media
    if isinstance(media, MessageMediaWebPage):
        return False, None, None

    return True, MEDIA_UNKNOWN, media


class ChannelMonitor:
    def __init__(self, client: TelegramClient, settings: Settings, settings_service: SettingsService, processor, publisher, stats_service):
        self.client = client
        self.settings = settings
        self.settings_service = settings_service
        self.processor = processor
        self.publisher = publisher
        self.stats_service = stats_service
        self.customizer = PostCustomizer(settings_service)
        self._handler = None
        self._last_forward_time = 0.0
        self._process_lock = asyncio.Lock()

    async def start(self) -> None:
        if await self.customizer.is_paused():
            logger.info("Monitor is paused")
            return

        sources = await self.settings_service.get_source_channels()
        if not sources:
            sources = self.settings.source_channels
        if not sources:
            logger.warning("No source channels configured")
            return

        dest = await self.settings_service.get_dest_channel()
        if not dest:
            dest = self.settings.dest_channel_username or self.settings.dest_channel_id
        if not dest:
            logger.warning("No destination channel configured")
            return

        logger.info("Monitoring %d source channels → %s", len(sources), dest)

        @self.client.on(NewMessage(chats=sources))
        async def _handler(event: NewMessage.Event) -> None:
            async with self._process_lock:
                await self._process_message(event)

        self._handler = _handler
        logger.info("Channel monitor started")

    async def _process_message(self, event: NewMessage.Event) -> None:
        try:
            source_channel_id = event.chat_id
            source_message_id = event.message.id

            if await self.publisher.is_already_processed(source_channel_id, source_message_id):
                logger.info("Skipping already processed msg %d from channel %d", source_message_id, source_channel_id)
                return

            has_media, media_type, media_obj = _detect_media(event)

            text = event.message.text or event.message.message or ""
            if not text and not has_media:
                return

            text = await self.customizer.customize(text)
            if text is None:
                return

            affiliate_tag = await self.settings_service.get_affiliate_tag()
            if not affiliate_tag:
                affiliate_tag = self.settings.default_affiliate_tag
            if not affiliate_tag:
                return

            domain = await self.settings_service.get("amazon_domain", "")
            if not domain:
                domain = self.settings.default_amazon_domain

            modified, asins, replaced = await self.processor.process(
                text,
                affiliate_tag=affiliate_tag,
                amazon_domain=domain,
            )
            if replaced == 0:
                logger.debug("No Amazon links found, skipping")
                return

            dest = await self.settings_service.get_dest_channel()
            if not dest:
                dest = self.settings.dest_channel_username or self.settings.dest_channel_id
            if not dest:
                return

            delay = await self.customizer.get_delay()
            if delay > 0:
                elapsed = asyncio.get_event_loop().time() - self._last_forward_time
                wait = max(0, delay - elapsed)
                if wait > 0:
                    logger.debug("Waiting %.1fs before next forward", wait)
                    await asyncio.sleep(wait)

            published_id = await self.publisher.publish(
                source_channel_id=source_channel_id,
                source_message_id=source_message_id,
                dest_channel=dest,
                text=modified,
                original_text=text,
                asins=asins,
                links_replaced=replaced,
                user_id=1,
                pipeline_id=1,
                had_media=has_media,
                media_type=media_type,
                media_obj=media_obj,
            )

            if published_id is not None:
                self._last_forward_time = asyncio.get_event_loop().time()
                await self.stats_service.record_publish(user_id=1, pipeline_id=1)

        except Exception as e:
            logger.error("Message processing error: %s", e, exc_info=True)

    async def stop(self) -> None:
        if self._handler:
            self.client.remove_event_handler(self._handler)
            self._handler = None
            logger.info("Channel monitor stopped")

    async def restart(self) -> None:
        await self.stop()
        await self.start()
