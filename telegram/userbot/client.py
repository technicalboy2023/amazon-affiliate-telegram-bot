import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from config.settings import Settings
from utils.encryption import decrypt

logger = logging.getLogger(__name__)


class UserbotClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: TelegramClient | None = None
        self._running = False

    @property
    def client(self) -> TelegramClient | None:
        return self._client

    async def start(self) -> TelegramClient:
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Disconnected previous userbot client")
        session_string = await self._load_session()
        self._client = TelegramClient(
            StringSession(session_string) if session_string else StringSession(),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
            connection_retries=5,
            retry_delay=3,
        )
        await self._client.connect()
        if session_string:
            if not await self._client.is_user_authorized():
                logger.warning("Saved session is invalid")
                self._client = TelegramClient(
                    StringSession(),
                    self.settings.telegram_api_id,
                    self.settings.telegram_api_hash,
                    connection_retries=5,
                    retry_delay=3,
                )
                await self._client.connect()
                return self._client
            self._running = True
            me = await self._client.get_me()
            logger.info("Userbot connected as @%s", me.username)
        else:
            logger.info("No saved session. Use /login to authenticate")
        return self._client

    async def stop(self) -> None:
        self._running = False
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Userbot disconnected")

    async def _load_session(self) -> str | None:
        from database.engine import create_engine, create_session_factory
        engine = create_engine(self.settings.database_url)
        sf = create_session_factory(engine)
        try:
            async with sf() as session:
                from sqlalchemy import select

                from database.models.telegram_account import TelegramAccount
                from database.models.user import User
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
        finally:
            await engine.dispose()
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
