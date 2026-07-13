#!/usr/bin/env python3
"""
Standalone script to generate a Telethon session FILE.

The session file (userbot_session.session) will be created in the current
directory. Run this on the server via SSH — the session file is saved
directly in the project folder where the bot can use it.

How to use:
  1. cd ~/amazon-affiliate-telegram-bot
  2. source .venv/bin/activate
  3. python scripts/generate_session.py
  4. Enter the OTP code you receive on Telegram
  5. Session file is auto-saved in the current directory
  6. Restart the alwaysdata service
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

# Auto-load .env file so user doesn't need to enter API ID/Hash/Phone manually
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


async def main() -> None:
    print("=" * 60)
    print("  TELEGRAM SESSION FILE GENERATOR")
    print("  Generates userbot_session.session file")
    print("=" * 60)
    print()

    # Auto-read from .env if available
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    phone = os.getenv("TELEGRAM_PHONE", "").strip()

    if not api_id:
        api_id = input("Enter TELEGRAM_API_ID: ").strip()
    if not api_hash:
        api_hash = input("Enter TELEGRAM_API_HASH: ").strip()
    if not phone:
        phone = input("Enter phone (e.g., +918009164899): ").strip()

    if not api_id or not api_hash or not phone:
        print("❌ API_ID, API_HASH and PHONE are required!")
        print("   Set them in .env or enter manually.")
        sys.exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ TELEGRAM_API_ID must be a number! Check your .env")
        sys.exit(1)

    # Use file-based session - same as client.py
    # Telethon auto-saves to "userbot_session.session"
    client = TelegramClient(
        "userbot_session",  # file-based session (auto-saved by Telethon)
        api_id,
        api_hash,
        device_model="SM-S918B",
        system_version="SDK 34",
        app_version="10.10.0.4377",
        lang_code="en",
    )

    try:
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"\n✅ Already logged in as @{me.username or me.first_name}")
        else:
            print(f"\n📱 Requesting code for {phone}...")
            await client.send_code_request(phone)
            print("✅ Code sent! Check your Telegram app.")
            print()

            code = input("Enter the code you received: ").strip()
            code = code.replace(" ", "")

            if not code:
                print("❌ Code cannot be empty!")
                sys.exit(1)

            try:
                me = await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("🔐 2FA is enabled! Enter your password: ").strip()
                me = await client.sign_in(password=password)

            print(f"\n✅ Login successful! Logged in as @{me.username or me.first_name}")

        # Session is auto-saved to "userbot_session.session" by Telethon
        session_file = Path("userbot_session.session")
        if session_file.exists():
            print(f"\n✅ Session file created: {session_file.resolve()}")
            print(f"   File size: {session_file.stat().st_size} bytes")
        else:
            print("\n⚠️ Session file not found. Using in-memory session only.")
            print("   Try running with: TelegramClient('userbot_session', ...)")

        print("\n" + "=" * 60)
        print("📋 NEXT STEPS:")
        print("=" * 60)
        print("1. Session file is already in the project folder!")
        print("2. Restart the alwaysdata service (Advanced → Services → Save)")
        print("3. Bot will auto-connect using the session file!")
        print()

    except PhoneNumberInvalidError:
        print("❌ Invalid phone number! Include country code (e.g., +91...)")
    except PhoneCodeInvalidError:
        print("❌ Invalid code! Please try again.")
    except PhoneCodeExpiredError:
        print("⌛ Code expired! Please run again for a fresh code.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
