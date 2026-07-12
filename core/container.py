from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from telethon import TelegramClient

    from config.settings import Settings
    from services.channel_monitor import ChannelMonitor
    from services.cleanup.service import CleanupService
    from services.link_engine.engine import LinkEngine
    from services.message_processor import MessageProcessor
    from services.message_publisher import MessagePublisher
    from services.settings_service import SettingsService
    from services.stats_service import StatsService
    from services.user_service import UserService
    from telegram.userbot.client import UserbotClient
    from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container


@dataclass
class Container:
    settings: Settings = field(default=None)

    bot: Bot = field(default=None)
    dispatcher: Dispatcher = field(default=None)
    userbot_client: UserbotClient = field(default=None)
    userbot: TelegramClient = field(default=None)

    session_factory: async_sessionmaker[AsyncSession] = field(default=None)

    link_engine: LinkEngine = field(default=None)
    channel_monitor: ChannelMonitor = field(default=None)
    message_processor: MessageProcessor = field(default=None)
    message_publisher: MessagePublisher = field(default=None)
    user_service: UserService = field(default=None)
    stats_service: StatsService = field(default=None)
    cleanup_service: CleanupService = field(default=None)
    settings_service: SettingsService = field(default=None)

    bot_rate_limiter: RateLimiter = field(default=None)
    resolver_rate_limiter: RateLimiter = field(default=None)

    async def shutdown(self) -> None:
        logger.info("Shutting down container services...")
        if self.channel_monitor:
            await self.channel_monitor.stop()
        if self.userbot_client:
            await self.userbot_client.stop()
        if self.userbot and self.userbot.is_connected():
            await self.userbot.disconnect()
        logger.info("Container shutdown complete")
