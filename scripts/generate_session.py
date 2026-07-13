#!/usr/bin/env python3
"""
Standalone script to generate a Telethon session FILE locally.

The session file (userbot_session.session) will be created in the current
directory. Upload this file to the server so the bot can use it.

This matches the file-based session approach used by the bot (client.py).

How to use:
  1. Copy this script to your local machine (Windows/Mac/Linux)
  2. Install telethon: pip install telethon
  3. Run: python generate_session.py
  4. Enter your API ID, API Hash, and phone number
  5. Enter the OTP code you receive
  6. Upload the generated "userbot_session.session" file to the server
  7. Restart the alwaysdata service
"""

import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)


async def main() -> None:
    print("=" * 60)
    print("  TELEGRAM SESSION FILE GENERATOR")
    print("  Generates userbot_session.session file")
    print("=" * 60)
    print()

    api_id = input("Enter your TELEGRAM_API_ID: ").strip()
    api_hash = input("Enter your TELEGRAM_API_HASH: ").strip()
    phone = input("Enter your phone number (e.g., +918009164899): ").strip()

    if not api_id or not api_hash or not phone:
        print("❌ All fields are required!")
        sys.exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API ID must be a number!")
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
            print(f"\n⚠️ Session file not found. Using in-memory session only.")
            print(f"   Try running with: TelegramClient('userbot_session', ...)")

        print("\n" + "=" * 60)
        print("📋 NEXT STEPS:")
        print("=" * 60)
        print("1. Upload the 'userbot_session.session' file to the server")
        print("2. SSH command:")
        print(f"   scp userbot_session.session achal@ssh-achal.alwaysdata.net:/home/achal/amazon-affiliate-telegram-bot/")
        print("3. Restart the alwaysdata service")
        print("4. Bot will auto-connect using the session file!")
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
