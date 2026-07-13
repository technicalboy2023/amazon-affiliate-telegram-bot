"""
Phone + OTP login handler using Telethon's send_code_request / sign_in flow.

Replaces the old QR-code approach because QR sessions are tied to the device
and expire frequently. With phone-based auth the session is self-contained
(no external device dependency) and stays valid much longer.
"""

import asyncio
import logging

from aiogram import types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from config.settings import get_settings
from core.container import get_container
from database.models.telegram_account import TelegramAccount
from database.repositories.telegram_account_repo import TelegramAccountRepository
from sqlalchemy import update as sql_update
from database.repositories.user_repo import UserRepository
from utils.encryption import encrypt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FSM states for the multi-step login conversation
# ---------------------------------------------------------------------------

class LoginStates(StatesGroup):
    WAITING_PHONE = State()
    WAITING_OTP = State()
    WAITING_PASSWORD = State()


# Per-user in-memory state for the ongoing login attempt.
# Key: Telegram user_id, Value: dict with client/phone/phone_code_hash.
_login_data: dict[int, dict] = {}

# How long we keep a stale login session alive before the user must
# start over (seconds).
_LOGIN_TIMEOUT = 300  # 5 minutes – Telethon OTP codes last ~5 min


def _cleanup_login(user_id: int) -> None:
    """Disconnect & remove any in-progress login state for *user_id*."""
    entry = _login_data.pop(user_id, None)
    if entry is None:
        return
    client: TelegramClient = entry["client"]
    try:
        if client.is_connected():
            client.disconnect()
    except Exception:
        pass


async def _schedule_cleanup(user_id: int, delay: float = _LOGIN_TIMEOUT) -> None:
    """Schedule a delayed cleanup so stale sessions don't leak."""
    await asyncio.sleep(delay)
    entry = _login_data.get(user_id)
    if entry is not None and not entry.get("finalized", False):
        logger.warning("Login session timeout for user %d – cleaning up", user_id)
        _cleanup_login(user_id)


# ---------------------------------------------------------------------------
# /login  →  ask for phone number
# ---------------------------------------------------------------------------

async def cmd_login(message: types.Message, state: FSMContext) -> None:
    """Start the phone-based login flow."""
    user_id = message.from_user.id

    # Tear down any leftover login client for this user
    _cleanup_login(user_id)

    await state.set_state(LoginStates.WAITING_PHONE)
    await message.answer(
        "📱 *Phone Login*\n\n"
        "Please send your phone number with country code.\n"
        "Example: `+911234567890`\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 1 – phone number received → request OTP
# ---------------------------------------------------------------------------

async def process_phone(message: types.Message, state: FSMContext) -> None:
    """Handle phone number input – send verification code."""
    phone = message.text.strip()

    if not phone.startswith("+"):
        await message.answer(
            "❌ Phone must start with `+` and a country code.\n"
            "Example: `+911234567890`",
            parse_mode="Markdown",
        )
        return

    settings = get_settings()
    client = TelegramClient(
        StringSession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        device_model="Samsung Galaxy S23",
        system_version="Android 14",
        app_version="1.0.0",
        lang_code="en",
        connection_retries=5,
        retry_delay=3,
    )

    try:
        await client.connect()
        sent_code = await client.send_code_request(phone)

        _login_data[message.from_user.id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent_code.phone_code_hash,
            "finalized": False,
        }

        await state.set_state(LoginStates.WAITING_OTP)
        await message.answer(
            "✅ Verification code sent to your Telegram app / SMS.\n\n"
            "Please enter the code you received.\n"
            "If you don't see it, check Telegram → Settings → Privacy & Security → Active Sessions.\n\n"
            "Send /cancel to abort."
        )

        # Fire-and-forget cleanup guard
        asyncio.create_task(_schedule_cleanup(message.from_user.id))

    except PhoneNumberInvalidError:
        await message.answer(
            "❌ Invalid phone number. Include the country code.\n"
            "Example: `+911234567890`",
            parse_mode="Markdown",
        )
        await client.disconnect()
    except Exception as e:
        logger.error("Phone verification error: %s", e)
        await message.answer(f"❌ Error: {e}")
        await client.disconnect()


# ---------------------------------------------------------------------------
# Step 2 – OTP code received → sign in
# ---------------------------------------------------------------------------

async def process_otp(message: types.Message, state: FSMContext) -> None:
    """Handle OTP code input – attempt to sign in."""
    user_id = message.from_user.id
    data = _login_data.get(user_id)

    if data is None:
        await message.answer("❌ Session expired. Use /login to start again.")
        await state.clear()
        return

    code = message.text.strip().replace(" ", "")
    client: TelegramClient = data["client"]
    phone = data["phone"]
    phone_code_hash = data["phone_code_hash"]

    try:
        me = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        logger.info("Phone login successful for @%s", me.username)

        data["finalized"] = True
        _login_data.pop(user_id, None)  # remove from dict but KEEP client connected
        await state.clear()

        await _finalize_login(message, client, me, phone)

    except SessionPasswordNeededError:
        # 2FA is enabled – ask for the password
        await state.set_state(LoginStates.WAITING_PASSWORD)
        await message.answer(
            "🔐 Two-factor authentication is enabled on this account.\n\n"
            "Please enter your 2FA password:"
        )
    except PhoneCodeInvalidError:
        await message.answer("❌ Invalid code. Please check and try again.")
    except Exception as e:
        logger.error("OTP verification error: %s", e)
        await message.answer(f"❌ Login failed: {e}")


# ---------------------------------------------------------------------------
# Step 3 (optional) – 2FA password
# ---------------------------------------------------------------------------

async def process_password(message: types.Message, state: FSMContext) -> None:
    """Handle 2FA password – complete the sign-in."""
    user_id = message.from_user.id
    data = _login_data.get(user_id)

    if data is None:
        await message.answer("❌ Session expired. Use /login to start again.")
        await state.clear()
        return

    password = message.text.strip()
    client: TelegramClient = data["client"]
    phone = data["phone"]

    try:
        me = await client.sign_in(password=password)
        logger.info("Phone login (2FA) successful for @%s", me.username)

        data["finalized"] = True
        _login_data.pop(user_id, None)  # remove from dict but KEEP client connected
        await state.clear()

        await _finalize_login(message, client, me, phone)

    except Exception as e:
        logger.error("2FA password error: %s", e)
        await message.answer(f"❌ Login failed: {e}")


# ---------------------------------------------------------------------------
# /cancel  – abort the login flow
# ---------------------------------------------------------------------------

async def cmd_cancel_login(message: types.Message, state: FSMContext) -> None:
    """Cancel the in-progress login."""
    _cleanup_login(message.from_user.id)
    await state.clear()
    await message.answer("❌ Login cancelled.")


# ---------------------------------------------------------------------------
# Common finalisation – save session string, restart monitoring
# ---------------------------------------------------------------------------

async def _finalize_login(
    message: types.Message,
    client: TelegramClient,
    me,
    phone: str,
) -> None:
    """Persist the session to the database and restart the channel monitor."""
    raw_session = client.session.save()
    encrypted = encrypt(raw_session)
    encrypted_phone = encrypt(phone)

    container = get_container()
    async with container.session_factory() as session:
        # Deactivate old accounts first to avoid stale session accumulation
        await session.execute(
            sql_update(TelegramAccount)
            .where(TelegramAccount.is_active.is_(True))
            .values(is_active=False, status="replaced")
        )

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
            phone_number_encrypted=encrypted_phone,
            session_string_encrypted=encrypted,
            username=me.username,
            display_name=me.first_name,
            status="connected",
            is_active=True,
        )
        await session.commit()

    # Stop the current monitor before swapping the client out
    if container.channel_monitor:
        await container.channel_monitor.stop()

    container.userbot = client
    await container.userbot_client.replace_client(client)

    # Re-create publisher + monitor with the new client
    from services.message_publisher import MessagePublisher
    from telegram.userbot.handlers.monitor import ChannelMonitor

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

    await message.answer("✅ Login successful! Monitoring started.")


# ---------------------------------------------------------------------------
# Registration helper – called from main.py at startup
# ---------------------------------------------------------------------------

def register_login_handlers(dp) -> None:
    """Register all login-related message handlers on the Aiogram dispatcher."""
    dp.message.register(cmd_login, Command("login"))
    dp.message.register(process_phone, StateFilter(LoginStates.WAITING_PHONE))
    dp.message.register(process_otp, StateFilter(LoginStates.WAITING_OTP))
    dp.message.register(process_password, StateFilter(LoginStates.WAITING_PASSWORD))
    dp.message.register(cmd_cancel_login, Command("cancel"), StateFilter(LoginStates))
