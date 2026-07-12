import asyncio
import io
import logging

import qrcode
from aiogram import types
from aiogram.types import BufferedInputFile
from telethon import TelegramClient
from telethon.sessions import StringSession

from config.settings import get_settings
from core.container import get_container
from database.repositories.telegram_account_repo import TelegramAccountRepository
from database.repositories.user_repo import UserRepository
from utils.encryption import encrypt

logger = logging.getLogger(__name__)

_login_client: TelegramClient | None = None


def _get_login_client() -> TelegramClient:
    global _login_client
    if _login_client is None:
        settings = get_settings()
        _login_client = TelegramClient(
            StringSession(),
            settings.telegram_api_id,
            settings.telegram_api_hash,
            device_model="Samsung Galaxy S23",
            system_version="Android 14",
            app_version="1.0.0",
            lang_code="en",
        )
    return _login_client


async def cmd_login(message: types.Message) -> None:
    """Login via QR code scan."""
    global _login_client

    if _login_client is not None:
        if _login_client.is_connected():
            await _login_client.disconnect()
        _login_client = None

    client = _get_login_client()
    try:
        await client.connect()
    except Exception as e:
        logger.error("Login connect error: %s", e)
        await message.answer(f"Connection error: {e}")
        return

    try:
        qr_login = await client.qr_login()
    except Exception as e:
        logger.error("QR login error: %s", e)
        await message.answer(f"QR login failed: {e}")
        return

    img = qrcode.make(qr_login.url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    await message.answer_photo(
        BufferedInputFile(buf.getvalue(), filename="qr.png"),
        caption=(
            "Scan this QR code with your Telegram app (Settings → Devices → Scan QR)\n\n"
            "The code expires in 60 seconds."
        ),
    )

    asyncio.create_task(_wait_for_qr_login(client, qr_login, message))


async def _wait_for_qr_login(
    client: TelegramClient,
    qr_login,
    message: types.Message,
) -> None:
    try:
        me = await asyncio.wait_for(qr_login.wait(), timeout=60)
        logger.info("QR login successful for @%s", me.username)
        await _finalize_login(message, client, me)
    except TimeoutError:
        logger.info("QR login timed out")
        await message.answer("QR code expired. Use /login to try again.")
    except Exception as e:
        logger.error("QR login failed: %s", e)
        await message.answer(f"Login failed: {e}")


async def _finalize_login(
    message: types.Message, client: TelegramClient, me,
) -> None:
    global _login_client
    raw_session = client.session.save() if hasattr(client, "session") else StringSession.save(client.session)
    encrypted = encrypt(raw_session)

    container = get_container()
    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        tg_repo = TelegramAccountRepository(session)
        user, _created = await user_repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        await tg_repo.create(
            user_id=user.id,
            telegram_user_id=me.id,
            phone_number_encrypted="",
            session_string_encrypted=encrypted,
            username=me.username,
            display_name=me.first_name,
            status="connected",
            is_active=True,
        )
        await session.commit()

    _login_client = None
    if container.channel_monitor:
        await container.channel_monitor.stop()
    if container.message_publisher:
        pass

    container.userbot = client
    container.userbot_client._client = client
    container.userbot_client._running = True

    from services.channel_monitor import ChannelMonitor
    from services.message_publisher import MessagePublisher
    container.message_publisher = MessagePublisher(
        userbot=client,
        duplicate_checker=container.duplicate_checker,
        session_factory=container.session_factory,
    )
    channel_monitor = ChannelMonitor(
        client=client,
        settings=container.settings,
        settings_service=container.settings_service,
        processor=container.message_processor,
        publisher=container.message_publisher,
        stats_service=container.stats_service,
    )
    container.channel_monitor = channel_monitor
    await channel_monitor.start()

    await message.answer("Login successful! Monitoring started.")
