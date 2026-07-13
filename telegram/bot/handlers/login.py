"""
Simplified login handler using file-based session approach.

Instead of a complex FSM phone/OTP flow (which triggers Telegram security
from VPS IPs), the user generates the session file locally on their machine
and uploads it to the server. This completely bypasses VPS login blocks.

Required steps:
  1. pip install telethon on local machine
  2. Run scripts/generate_session.py locally
  3. Upload the generated "userbot_session.session" file to the server
  4. Restart the service
"""

import logging

from aiogram import types

from core.container import get_container

logger = logging.getLogger(__name__)


async def cmd_login(message: types.Message) -> None:
    """Show login instructions for file-based session."""
    container = get_container()
    userbot_connected = bool(container.userbot and container.userbot.is_connected())

    if userbot_connected:
        me = await container.userbot.get_me()
        await message.answer(
            f"✅ Userbot is already connected as @{me.username or me.first_name}!"
        )
        return

    phone = container.settings.telegram_phone or "Not configured"

    instructions = (
        "📱 *File-Based Session Login*\n\n"
        "Since the bot runs on a server (alwaysdata), Telegram blocks direct\n"
        "OTP login from here. Instead, generate the session on your local machine:\n\n"
        "1️⃣ On your LOCAL PC/phone, install Telethon:\n"
        "   `pip install telethon`\n\n"
        "2️⃣ Run the session generator:\n"
        "   `python scripts/generate_session.py`\n\n"
        "3️⃣ Enter your API ID, API Hash, and phone number\n\n"
        "4️⃣ Enter the OTP code you receive\n\n"
        "5️⃣ Upload the generated file to the server:\n"
        "   `userbot_session.session`\n\n"
        "6️⃣ Restart the service\n\n"
        f"📞 Configured phone: `{phone}`\n"
        "❓ Need help? Check `guide/alwaysdata-setup-guide.txt`"
    )

    await message.answer(instructions, parse_mode="Markdown")
