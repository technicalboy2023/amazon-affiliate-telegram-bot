#!/usr/bin/env python3
"""
Import a Telethon session string into the bot database.

Run this on the alwaysdata server after generating a session string
locally using scripts/generate_session.py.

Usage:
    cd /home/achal/amazon-affiliate-telegram-bot
    .venv/bin/python scripts/import_session.py '<session_string>'

Or without argument (will prompt):
    .venv/bin/python scripts/import_session.py

This creates a TelegramAccount entry in the database so the bot
can use this session to connect as a userbot.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from telethon import TelegramClient
from telethon.sessions import StringSession

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")
from utils.encryption import encrypt

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    # Get session string from argument or prompt
    session_string = None
    if len(sys.argv) > 1:
        session_string = sys.argv[1].strip()

    if not session_string:
        print("\n📋 Paste your session string (from generate_session.py output):")
        session_string = input().strip()

    if not session_string:
        print("❌ No session string provided!")
        print("Usage: .venv/bin/python scripts/import_session.py '<session_string>'")
        sys.exit(1)

    # Verify the session string by connecting
    print("\n🔍 Verifying session string...")

    try:
        client = TelegramClient(
            StringSession(session_string),
            int(os.getenv("TELEGRAM_API_ID", "0")),
            os.getenv("TELEGRAM_API_HASH", ""),
        )
        await client.connect()

        if not await client.is_user_authorized():
            print("❌ Session string is invalid or expired!")
            await client.disconnect()
            sys.exit(1)

        me = await client.get_me()
        print(f"✅ Session valid! Logged in as @{me.username or me.first_name}")
        print(f"   User ID: {me.id}")
        await client.disconnect()
    except Exception as e:
        print(f"❌ Session verification failed: {e}")
        sys.exit(1)

    # Import to database
    print("\n💾 Saving session to database...")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env!")
        sys.exit(1)

    # Fix URL for sync engine (remove +asyncpg)
    sync_url = db_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    try:
        with engine.begin() as conn:
            admin_id = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
            if not admin_id:
                print("❌ ADMIN_TELEGRAM_ID not found in .env!")
                sys.exit(1)

            # Get or create user
            row = conn.execute(
                text("SELECT id FROM users WHERE telegram_id = :tid LIMIT 1"),
                {"tid": admin_id},
            ).fetchone()

            if not row:
                result = conn.execute(
                    text("INSERT INTO users (telegram_id, is_admin, is_active) VALUES (:tid, true, true) RETURNING id"),
                    {"tid": admin_id},
                )
                user_id = result.scalar_one()
                print(f"   Created user with id={user_id}")
            else:
                user_id = row[0]
                print(f"   Found user with id={user_id}")

            # Deactivate old accounts
            conn.execute(
                text("UPDATE telegram_accounts SET is_active = false, status = 'replaced' WHERE is_active = true")
            )

            # Encrypt the session string before storing
            encrypted_session = encrypt(session_string)

            # Insert new session
            result = conn.execute(
                text("""
                    INSERT INTO telegram_accounts
                    (user_id, telegram_user_id, session_string_encrypted,
                     username, display_name, is_active, status, last_connected_at)
                    VALUES (:uid, :tgid, :session, :username, :display, true, 'connected', NOW())
                    RETURNING id
                """),
                {
                    "uid": user_id,
                    "tgid": me.id,
                    "session": encrypted_session,
                    "username": me.username or "",
                    "display": me.first_name or "",
                },
            )
            account_id = result.scalar_one()
            print(f"\n✅ Session imported and encrypted successfully! (account_id={account_id})")
            print("   Bot will use this session on next restart.")

    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
