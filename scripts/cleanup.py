#!/usr/bin/env python3
"""Standalone cleanup — run via AlwaysData Scheduled Tasks every 7 days.

Cleans old rows from high-volume tables while preserving all user config,
Telegram login sessions, pipelines, and settings.

Safe to run while the bot is active (SQLite WAL mode handles concurrency).
"""

import logging
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "affiliate.db"
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_FILE = LOG_DIR / "cleanup.log"
RETENTION_DAYS = 7

CLEANABLE = [
    {
        "table": "processed_messages",
        "column": "processed_at",
        "label": "forwards",
    },
    {
        "table": "duplicate_cache",
        "column": "first_seen_at",
        "label": "duplicate cache",
    },
    {
        "table": "daily_stats",
        "column": "date",
        "label": "daily stats",
    },
]

SAFE_TABLES = [
    "users",
    "telegram_accounts",
    "automation_pipelines",
    "source_channels",
    "dest_channels",
    "affiliate_tags",
    "app_settings",
]


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )


def verify_db() -> bool:
    if not DB_PATH.exists():
        logging.error("Database not found: %s", DB_PATH)
        return False
    return True


def verify_tables(cursor: sqlite3.Cursor) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cursor.fetchall()}
    missing = [t["table"] for t in CLEANABLE if t["table"] not in existing]
    if missing:
        logging.warning("Tables not found (first run?): %s", missing)
    for table in SAFE_TABLES:
        if table not in existing:
            logging.warning("Expected table missing: %s", table)
    return True


def drop_orphan_tables(cur: sqlite3.Cursor) -> None:
    """Drop tables that no longer have a model (leftover from refactors)."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cur.fetchall()}
    orphan = {"cleanup_history"}
    for name in orphan & existing:
        cur.execute(f"DROP TABLE IF EXISTS {name}")
        logging.info("Dropped orphan table: %s", name)


def clean() -> dict[str, int]:
    cutoff_dt = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    cutoff_date = cutoff_dt.date().isoformat()
    cutoff_iso = cutoff_dt.isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    cur = conn.cursor()

    results: dict[str, int] = {}
    drop_orphan_tables(cur)

    try:
        for tbl in CLEANABLE:
            table = tbl["table"]
            column = tbl["column"]
            cutoff = cutoff_date if column == "date" else cutoff_iso
            op = "<=" if column == "date" else "<"
            cur.execute(f"DELETE FROM {table} WHERE {column} {op} ?", (cutoff,))
            deleted = cur.rowcount
            results[tbl["label"]] = deleted
            logging.info("Cleaned %s: %d rows deleted (cutoff=%s)", tbl["label"], deleted, cutoff)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return results


def main() -> None:
    setup_logging()
    logging.info("=" * 50)
    logging.info("Cleanup started (retention=%d days)", RETENTION_DAYS)

    if not verify_db():
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
        verify_tables(conn.cursor())
        conn.close()
    except sqlite3.Error as e:
        logging.error("DB connection failed: %s", e)
        return

    results = clean()
    logging.info("Cleanup complete: %s", results)
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
