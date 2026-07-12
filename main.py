import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable
from typing import Any

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Message

from config.settings import get_settings, validate_runtime_settings
from core.container import Container, set_container
from database.engine import create_engine, create_session_factory, init_db
from services.duplicate_checker import DuplicateChecker
from services.link_engine.engine import LinkEngine
from services.link_engine.extractor import UrlExtractor
from services.link_engine.providers.amazon import AmazonProvider
from services.link_engine.registry import ProviderRegistry
from services.link_engine.resolver import UrlResolver
from services.message_processor import MessageProcessor
from services.message_publisher import MessagePublisher
from services.settings_service import SettingsService
from services.stats_service import StatsService
from services.user_service import UserService
from telegram.bot.handlers.login import cmd_login
from telegram.bot.handlers.start import (
    cmd_add_block,
    cmd_add_replace,
    cmd_add_source,
    cmd_affiliate,
    cmd_clear_affiliate,
    cmd_clear_footer,
    cmd_clear_header,
    cmd_config,
    cmd_dest,
    cmd_domain,
    cmd_errors,
    cmd_help,
    cmd_history,
    cmd_list_blocks,
    cmd_list_replaces,
    cmd_logout,
    cmd_pause,
    cmd_ping,
    cmd_reload,
    cmd_remove_block,
    cmd_remove_dest,
    cmd_remove_replace,
    cmd_remove_source,
    cmd_resume,
    cmd_set_delay,
    cmd_set_footer,
    cmd_set_header,
    cmd_sources,
    cmd_start,
    cmd_stats,
    cmd_status,
    cmd_stop,
)
from telegram.userbot.client import UserbotClient
from telegram.userbot.handlers.monitor import ChannelMonitor
from utils.logging import setup_logging

logger = logging.getLogger("main")

container = Container()


async def init_container() -> None:
    settings = get_settings()
    container.settings = settings

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    container.session_factory = session_factory

    await init_db(engine)

    provider_registry = ProviderRegistry()
    amazon = AmazonProvider()
    provider_registry.register(amazon)

    resolver = UrlResolver(
        timeout_seconds=settings.url_resolve_timeout,
    )
    extractor = UrlExtractor()

    link_engine = LinkEngine(
        registry=provider_registry,
        extractor=extractor,
        resolver=resolver,
    )
    container.link_engine = link_engine

    container.user_service = UserService(session_factory)
    admin_user = await container.user_service.ensure_admin(
        telegram_id=settings.admin_telegram_id,
    )
    await container.user_service.ensure_default_setup(
        user_id=admin_user.id,
        affiliate_tag=settings.default_affiliate_tag,
    )
    container.duplicate_checker = DuplicateChecker(
        session_factory,
        window_hours=settings.duplicate_window_hours,
    )
    container.settings_service = SettingsService(session_factory)
    container.stats_service = StatsService(session_factory)

    container.message_processor = MessageProcessor(
        link_engine,
        user_id=settings.default_user_id,
        pipeline_id=settings.default_pipeline_id,
        telegram_account_id=settings.default_telegram_account_id,
    )

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    container.bot = bot
    container.dispatcher = dp

    @dp.message.outer_middleware()
    async def admin_check(
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user and event.from_user.id != settings.admin_telegram_id:
            await event.answer("⛔ Unauthorized.")
            return
        return await handler(event, data)

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_status, Command("status"))
    dp.message.register(cmd_config, Command("config"))
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_history, Command("history"))
    dp.message.register(cmd_errors, Command("errors"))
    dp.message.register(cmd_ping, Command("ping"))
    dp.message.register(cmd_pause, Command("pause"))
    dp.message.register(cmd_stop, Command("stop"))
    dp.message.register(cmd_resume, Command("resume"))
    dp.message.register(cmd_logout, Command("logout"))
    dp.message.register(cmd_affiliate, Command("affiliate"))
    dp.message.register(cmd_clear_affiliate, Command("clear_affiliate"))
    dp.message.register(cmd_sources, Command("sources"))
    dp.message.register(cmd_add_source, Command("add_source"))
    dp.message.register(cmd_remove_source, Command("remove_source"))
    dp.message.register(cmd_dest, Command("dest"))
    dp.message.register(cmd_remove_dest, Command("remove_dest"))
    dp.message.register(cmd_domain, Command("domain"))
    dp.message.register(cmd_set_delay, Command("set_delay"))
    dp.message.register(cmd_add_replace, Command("add_replace"))
    dp.message.register(cmd_remove_replace, Command("remove_replace"))
    dp.message.register(cmd_list_replaces, Command("list_replaces"))
    dp.message.register(cmd_add_block, Command("add_block"))
    dp.message.register(cmd_remove_block, Command("remove_block"))
    dp.message.register(cmd_list_blocks, Command("list_blocks"))
    dp.message.register(cmd_set_header, Command("set_header"))
    dp.message.register(cmd_set_footer, Command("set_footer"))
    dp.message.register(cmd_clear_header, Command("clear_header"))
    dp.message.register(cmd_clear_footer, Command("clear_footer"))
    dp.message.register(cmd_reload, Command("reload"))
    dp.message.register(cmd_login, Command("login"))

    userbot_client = UserbotClient(settings)
    container.userbot_client = userbot_client

    try:
        client = await userbot_client.start()
        container.userbot = client

        container.message_publisher = MessagePublisher(
            userbot=client,
            duplicate_checker=container.duplicate_checker,
            session_factory=session_factory,
        )

        channel_monitor = ChannelMonitor(
            client=client,
            settings=settings,
            settings_service=container.settings_service,
            processor=container.message_processor,
            publisher=container.message_publisher,
            stats_service=container.stats_service,
        )
        container.channel_monitor = channel_monitor
        await channel_monitor.start()

        logger.info("Userbot connected and monitoring started")
    except Exception as e:
        logger.warning("Userbot not connected: %s", e)
        logger.info("Use /login to authenticate your Telegram account")


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_file, settings.log_max_size_mb, settings.log_backup_count)
    validate_runtime_settings(settings)

    logger.info("Starting Affiliate Bot (canonical architecture)")

    await init_container()
    set_container(container)

    await container.bot.set_my_commands([
        BotCommand(command="help", description="Show all commands"),
        BotCommand(command="status", description="Check bot status"),
        BotCommand(command="config", description="View all runtime settings"),
        BotCommand(command="stats", description="Today's statistics"),
        BotCommand(command="history", description="Recent forwarded messages"),
        BotCommand(command="errors", description="Recent errors"),
        BotCommand(command="ping", description="Health check"),
        BotCommand(command="pause", description="Pause forwarding"),
        BotCommand(command="stop", description="Stop monitoring"),
        BotCommand(command="resume", description="Resume forwarding"),
        BotCommand(command="logout", description="Disconnect userbot"),
        BotCommand(command="affiliate", description="Set affiliate tag"),
        BotCommand(command="clear_affiliate", description="Clear affiliate tag"),
        BotCommand(command="sources", description="List source channels"),
        BotCommand(command="add_source", description="Add source channel"),
        BotCommand(command="remove_source", description="Remove source channel"),
        BotCommand(command="dest", description="Set destination channel"),
        BotCommand(command="remove_dest", description="Clear destination channel"),
        BotCommand(command="domain", description="Set Amazon domain"),
        BotCommand(command="set_delay", description="Set forward delay (sec)"),
        BotCommand(command="add_replace", description="Add word replacement"),
        BotCommand(command="remove_replace", description="Remove replacement"),
        BotCommand(command="list_replaces", description="View replacements"),
        BotCommand(command="add_block", description="Block posts containing word"),
        BotCommand(command="remove_block", description="Remove block rule"),
        BotCommand(command="list_blocks", description="View block rules"),
        BotCommand(command="set_header", description="Add header to posts"),
        BotCommand(command="set_footer", description="Add footer to posts"),
        BotCommand(command="clear_header", description="Remove header"),
        BotCommand(command="clear_footer", description="Remove footer"),
        BotCommand(command="reload", description="Reload monitor settings"),
        BotCommand(command="login", description="Log in via QR code scan"),
    ])

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    try:
        await asyncio.gather(
            container.dispatcher.start_polling(container.bot),
            stop_event.wait(),
        )
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down...")
        await container.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
