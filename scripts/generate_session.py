#!/usr/bin/env python3
"""
Standalone script to generate a Telethon session STRING locally.

Use this on your LOCAL machine (not the server) to create a session
string that you can then import on the alwaysdata server via
scripts/import_session.py.

This bypasses Telegram's security blocks that happen when logging
in from a VPS/server IP (like alwaysdata in France).

How to use:
  1. Copy this script to your local machine (Windows/Mac/Linux)
  2. Install telethon: pip install telethon
  3. Run: python generate_session.py
  4. Enter your API ID, API Hash, and phone number
  5. Enter the OTP code you receive
  6. Copy the output session string
  7. SSH into alwaysdata and run: python import_session.py <session_string>
"""

import asyncio
import sys

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession


async def main() -> None:
    print("=" * 60)
    print("  TELEGRAM SESSION GENERATOR")
    print("  Run this on your LOCAL machine (not VPS)")
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

    client = TelegramClient(
        StringSession(),
        api_id,
        api_hash,
        device_model="SM-S918B",       # Samsung Galaxy S23 Ultra model code
        system_version="SDK 34",       # Android 14 API level
        app_version="10.10.0.4377",    # Real Telegram Android version
        lang_code="en",
    )

    try:
        await client.connect()
        print(f"\n📱 Requesting code for {phone}...")
        sent_code = await client.send_code_request(phone)
        print(f"✅ Code sent! Check your Telegram app.")
        print()

        code = input("Enter the code you received: ").strip()
        code = code.replace(" ", "")

        if not code:
            print("❌ Code cannot be empty!")
            sys.exit(1)

        try:
            me = await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
        except SessionPasswordNeededError:
            password = input("🔐 2FA is enabled! Enter your password: ").strip()
            me = await client.sign_in(password=password)

        print(f"\n✅ Login successful! Logged in as @{me.username or me.first_name}")

        # Save the session string
        session_string = client.session.save()
        print("\n" + "=" * 60)
        print("📋 YOUR SESSION STRING (copy this):")
        print("=" * 60)
        print(session_string)
        print("=" * 60)
        print()
        print("Now SSH into your alwaysdata server and run:")
        print(f"  python scripts/import_session.py {session_string[:20]}...")
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
