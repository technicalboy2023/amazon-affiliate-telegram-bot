"""
Login handler for file-based session setup.

Run scripts/generate_session.py via SSH to create the Telethon session file
(userbot_session.session) directly in the project directory — no local
machine or SCP upload needed. Then restart the alwaysdata service.
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
        "📱 *Session Login*\n\n"
        "Generate the session file directly on the server via SSH:\n\n"
        "1️⃣ SSH into alwaysdata:\n"
        "   `ssh achal@ssh-achal.alwaysdata.net`\n\n"
        "2️⃣ Activate venv and run:\n"
        "   `cd ~/amazon-affiliate-telegram-bot && source .venv/bin/activate`\n"
        "   `python scripts/generate_session.py`\n\n"
        "3️⃣ Enter the OTP code when prompted\n\n"
        "4️⃣ Restart the service (Advanced → Services → Save)\n\n"
        f"📞 Configured phone: `{phone}`\n"
        "❓ Need help? Check the `README.md` for full setup guide"
    )

    await message.answer(instructions, parse_mode="Markdown")
