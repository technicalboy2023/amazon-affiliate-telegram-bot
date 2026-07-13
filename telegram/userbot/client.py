import asyncio
import logging

from telethon import TelegramClient

from config.settings import Settings

logger = logging.getLogger(__name__)

KEEPALIVE_INTERVAL = 30


class UserbotClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: TelegramClient | None = None
        self._running = False
        self._watchdog_task: asyncio.Task | None = None
        self._on_reconnect_callback = None

    def set_on_reconnect(self, callback):
        self._on_reconnect_callback = callback

    @property
    def client(self) -> TelegramClient | None:
        return self._client

    async def start(self) -> TelegramClient:
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Disconnected previous userbot client")

        # Use file-based session like the other repo (telegram-auto-forwarding-bot).
        # Telethon auto-saves the session to "userbot_session.session" file.
        # On first run, client.start(phone=...) will prompt for OTP automatically.
        # On subsequent runs, the saved session is reused seamlessly.
        self._client = TelegramClient(
            "userbot_session",  # file-based session (auto-saved by Telethon)
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
            device_model="SM-S918B",
            system_version="SDK 34",
            app_version="10.10.0.4377",
            lang_code="en",
            connection_retries=5,
            retry_delay=3,
        )

        await self._client.connect()

        if await self._client.is_user_authorized():
            self._running = True
            me = await self._client.get_me()
            logger.info("Userbot reconnected as @%s", me.username)
            self._start_watchdog()
        elif self.settings.telegram_phone:
            # First-time setup: phone number is configured but no session file exists yet.
            # The user must run scripts/generate_session.py on their local machine
            # to create the session file, then upload it to the server.
            logger.info(
                "No saved session file found. "
                "Run scripts/generate_session.py on your local machine, "
                "then upload the 'userbot_session.session' file to the server."
            )
        else:
            logger.info(
                "No saved session and no phone configured. "
                "Set TELEGRAM_PHONE in .env and run scripts/generate_session.py locally."
            )

        return self._client

    async def replace_client(self, client: TelegramClient) -> None:
        self._stop_watchdog()
        if self._client and self._client.is_connected():
            await self._client.disconnect()
        self._client = client
        self._running = True
        self._start_watchdog()

    async def stop(self) -> None:
        self._running = False
        self._stop_watchdog()
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Userbot disconnected")

    async def ensure_connected(self) -> TelegramClient:
        if self._client and self._client.is_connected():
            return self._client
        return await self.start()

    def _start_watchdog(self) -> None:
        self._stop_watchdog()
        self._watchdog_task = asyncio.create_task(self._connection_watchdog())

    def _stop_watchdog(self) -> None:
        if self._watchdog_task is not None:
            self._watchdog_task.cancel()
            self._watchdog_task = None

    async def _connection_watchdog(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                if not self._running:
                    break
                if self._client and not self._client.is_connected():
                    logger.warning("Userbot disconnected. Reconnecting...")
                    await self._client.connect()
                    me = await self._client.get_me()
                    logger.info("Userbot reconnected as @%s", me.username)
                    if self._on_reconnect_callback:
                        await self._on_reconnect_callback()
                elif self._client:
                    await self._client.get_me()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Connection watchdog error: %s", e)
