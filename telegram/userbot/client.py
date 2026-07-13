import asyncio
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from config.settings import Settings
from utils.encryption import decrypt

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
        session_string = await self._load_session()
        self._make_client(session_string)
        await self._client.connect()
        if session_string:
            if not await self._client.is_user_authorized():
                logger.warning("Saved session is invalid")
                self._make_client(None)
                await self._client.connect()
                self._running = False
                return self._client
            self._running = True
            me = await self._client.get_me()
            logger.info("Userbot connected as @%s", me.username)
            self._start_watchdog()
        else:
            logger.info("No saved session. Use /login to authenticate")
        return self._client

    def _make_client(self, session_string: str | None) -> None:
        self._client = TelegramClient(
            StringSession(session_string) if session_string else StringSession(),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
            device_model="Samsung Galaxy S23",
            system_version="Android 14",
            app_version="1.0.0",
            lang_code="en",
            connection_retries=5,
            retry_delay=3,
        )

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

    async def _load_session(self) -> str | None:
        # Try to use the container's session factory if available (post-startup
        # reconnects). During initial startup the container hasn't been
        # set_container() yet, so we fall back to creating a temporary engine.
        try:
            from core.container import get_container
            container = get_container()
            if container.session_factory is not None:
                return await self._query_session(container.session_factory)
        except RuntimeError:
            pass
        # Fallback: startup path – container not fully initialised yet
        from database.engine import create_engine, create_session_factory
        engine = create_engine(self.settings.database_url)
        sf = create_session_factory(engine)
        try:
            return await self._query_session(sf)
        finally:
            await engine.dispose()

    async def _query_session(self, session_factory) -> str | None:
        from sqlalchemy import select

        from database.models.telegram_account import TelegramAccount
        from database.models.user import User
        async with session_factory() as session:
            stmt = (
                select(TelegramAccount)
                .join(User, TelegramAccount.user_id == User.id)
                .where(
                    TelegramAccount.is_active.is_(True),
                    TelegramAccount.session_string_encrypted.isnot(None),
                )
                .order_by(TelegramAccount.last_connected_at.desc().nullslast())
                .limit(1)
            )
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
        if account and account.session_string_encrypted:
            try:
                return decrypt(account.session_string_encrypted)
            except Exception as e:
                logger.error("Failed to decrypt session: %s", e)
        return None

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
