#!/usr/bin/env python3
"""Standalone cleanup — run via AlwaysData Scheduled Tasks every 7 days.

Cleans old rows from high-volume tables while preserving all user config,
Telegram login sessions, pipelines, and settings.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_FILE = LOG_DIR / "cleanup.log"
RETENTION_DAYS = 7

CLEANABLE = [
    {"table": "processed_messages", "column": "processed_at", "label": "forwards"},
    {"table": "duplicate_cache", "column": "first_seen_at", "label": "duplicate cache"},
    {"table": "daily_stats", "column": "date", "label": "daily stats"},
]


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    )


def get_database_url() -> str | None:
    load_dotenv(BASE_DIR / ".env")
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    logging.error("DATABASE_URL not found in .env")
    return None


def clean(url: str) -> dict[str, int]:
    cutoff_dt = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    cutoff_str = cutoff_dt.isoformat()
    engine = create_engine(url)
    results: dict[str, int] = {}

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cleanup_history"))

        existing = {
            row[0]
            for row in conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
        }

        for tbl in CLEANABLE:
            table = tbl["table"]
            if table not in existing:
                logging.warning("Table not found (first run?): %s", table)
                continue
            column = tbl["column"]
            cutoff = cutoff_str[:10] if column == "date" else cutoff_str
            op = "<=" if column == "date" else "<"
            result = conn.execute(text(f"DELETE FROM {table} WHERE {column} {op} :cutoff"), {"cutoff": cutoff})
            results[tbl["label"]] = result.rowcount
            logging.info("Cleaned %s: %d rows deleted", tbl["label"], result.rowcount)

    engine.dispose()
    return results


def main() -> None:
    setup_logging()
    logging.info("=" * 50)
    logging.info("Cleanup started (retention=%d days)", RETENTION_DAYS)

    url = get_database_url()
    if not url:
        return

    try:
        results = clean(url)
        logging.info("Cleanup complete: %s", results)
    except Exception as e:
        logging.error("Cleanup failed: %s", e)
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
