"""
Structured logging setup.

Configures both console and file logging with rotation.
All modules use `logging.getLogger(__name__)` -- this module
configures the root logger so everything is captured.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    max_size_mb: int = 5,
    backup_count: int = 3,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. None for console only.
        max_size_mb: Max log file size before rotation.
        backup_count: Number of rotated log files to keep.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Format: timestamp | level | module | message
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers (avoid duplicates on reload)
    root_logger.handlers.clear()

    # Console handler -- always active
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler -- if path provided
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Quiet noisy third-party loggers
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Logging configured: level=%s, file=%s", level, log_file)
