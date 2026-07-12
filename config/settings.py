"""
Application settings loaded from environment variables.

Uses pydantic-settings for validation and type coercion.
All configuration is centralized here -- no hardcoded values anywhere else.
"""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE_FILE = BASE_DIR / ".env.example"


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


def ensure_env_file() -> Path:
    """
    Ensure a local .env file exists.

    Development and first-run deployments should not fail with an opaque
    Pydantic validation error just because .env has not been created yet.
    We copy .env.example once, then explicit runtime validation reports which
    real values must be filled in.
    """
    if ENV_FILE.exists():
        return ENV_FILE
    if not ENV_EXAMPLE_FILE.exists():
        raise ConfigurationError(
            f"Missing {ENV_FILE} and template {ENV_EXAMPLE_FILE}. "
            "Create .env with the required application settings."
        )
    shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
    return ENV_FILE


def _parse_csv(value: str | list[str] | None) -> list[str]:
    """Parse comma-separated env values while also accepting JSON-style lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [part.strip() for part in stripped.split(",") if part.strip()]
    return []


class Settings(BaseSettings):
    """Application settings with env-based configuration."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Telegram Bot (Aiogram) ---
    bot_token: str = ""

    # --- Telegram Userbot (Telethon) ---
    telegram_api_id: int = Field(default=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", alias="TELEGRAM_API_HASH")

    # --- Admin ---
    admin_telegram_id: int = 0

    # --- Default Affiliate ---
    default_affiliate_tag: str = ""
    default_amazon_domain: str = "amazon.in"

    # --- Source Channels ---
    source_channels_csv: str = Field(default="", alias="SOURCE_CHANNELS")

    # --- Destination Channel ---
    dest_channel_id: int | None = None
    dest_channel_username: str | None = None

    # --- Database ---
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'affiliate.db'}"

    # --- System Defaults (single-user personal bot) ---
    default_user_id: int = 1
    default_pipeline_id: int = 1
    default_telegram_account_id: int = 1

    # --- Duplicate Detection ---
    duplicate_window_hours: int = 1  # 1 hour — same ASIN re-posted after 1h is allowed

    # --- Rate Limiting ---
    bot_rate_limit: int = 20
    resolver_rate_limit: int = 30

    # --- Logging ---
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "data" / "logs" / "affiliate.log")
    log_max_size_mb: int = 5
    log_backup_count: int = 3

    # --- Misc ---
    url_resolve_timeout: int = 10

    @property
    def source_channels(self) -> list[str]:
        """Source channel usernames parsed from comma-separated env value."""
        return _parse_csv(self.source_channels_csv)

    @property
    def data_dir(self) -> Path:
        """Data directory path."""
        return BASE_DIR / "data"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    ensure_env_file()
    settings = Settings()
    settings.ensure_directories()
    return settings


def validate_runtime_settings(settings: Settings | None = None) -> Settings:
    """
    Validate settings required to run the Telegram application.

    Alembic only needs DATABASE_URL and model metadata, so it should not fail
    because Telegram credentials are placeholders during initial setup.
    Runtime startup calls this function and gets a clear actionable message.
    """
    settings = settings or get_settings()
    required = {
        "BOT_TOKEN": settings.bot_token,
        "ADMIN_TELEGRAM_ID": settings.admin_telegram_id,
        "TELEGRAM_API_ID": settings.telegram_api_id,
        "TELEGRAM_API_HASH": settings.telegram_api_hash,
    }
    placeholders = {
        "your_bot_token_here",
        "your_api_hash_here",
        "yourtag-21",
        "NOT_SET",
        "not_set",
    }
    missing: list[str] = []
    for key, value in required.items():
        if value is None:
            missing.append(key)
            continue
        if isinstance(value, int):
            if value <= 0 or value in {123456, 12345678, 123456789}:
                missing.append(key)
            continue
        text = str(value).strip()
        if not text or text in placeholders:
            missing.append(key)

    if missing:
        joined = ", ".join(missing)
        raise ConfigurationError(
            f"Missing or placeholder runtime configuration: {joined}. "
            f"Edit {ENV_FILE} and provide real values before starting the bot."
        )
    return settings
