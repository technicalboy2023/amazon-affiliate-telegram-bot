from pathlib import Path

import pytest

from config.settings import ConfigurationError, Settings, validate_runtime_settings


def write_env(path: Path, content: str) -> Path:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_settings_loads_comma_separated_lists(tmp_path: Path) -> None:
    env_file = write_env(
        tmp_path / ".env",
        """
        BOT_TOKEN=123456:abc
        TELEGRAM_API_ID=987654
        TELEGRAM_API_HASH=hashvalue
        TELEGRAM_PHONE=+911111111111
        ADMIN_TELEGRAM_ID=555555
        DEFAULT_AFFILIATE_TAG=mytag-21
        SOURCE_CHANNELS=technicalgeardeals, kooltech3
        DATABASE_URL=sqlite+aiosqlite:///tmp/test.db
        """,
    )

    settings = Settings(_env_file=env_file)

    assert settings.source_channels == ["technicalgeardeals", "kooltech3"]
    assert settings.database_url == "sqlite+aiosqlite:///tmp/test.db"


def test_runtime_validation_reports_clear_missing_values(tmp_path: Path) -> None:
    env_file = write_env(
        tmp_path / ".env",
        """
        BOT_TOKEN=your_bot_token_here
        TELEGRAM_API_ID=12345678
        TELEGRAM_API_HASH=your_api_hash_here
        TELEGRAM_PHONE=+911111111111
        ADMIN_TELEGRAM_ID=123456789
        DEFAULT_AFFILIATE_TAG=yourtag-21
        DATABASE_URL=sqlite+aiosqlite:///tmp/test.db
        """,
    )
    settings = Settings(_env_file=env_file)

    with pytest.raises(ConfigurationError) as exc_info:
        validate_runtime_settings(settings)

    message = str(exc_info.value)
    assert "Missing or placeholder runtime configuration" in message
    assert "BOT_TOKEN" in message
    assert "ADMIN_TELEGRAM_ID" in message
    assert "DEFAULT_AFFILIATE_TAG" not in message
    assert "FERNET_KEY" not in message
    assert "TELEGRAM_API_ID" not in message
    assert "TELEGRAM_API_HASH" not in message


def test_runtime_validation_passes_for_realistic_values(tmp_path: Path) -> None:
    env_file = write_env(
        tmp_path / ".env",
        """
        BOT_TOKEN=123456:real_token
        TELEGRAM_API_ID=987654
        TELEGRAM_API_HASH=real_hash
        ADMIN_TELEGRAM_ID=555555
        DEFAULT_AFFILIATE_TAG=mytag-21
        DATABASE_URL=sqlite+aiosqlite:///tmp/test.db
        """,
    )
    settings = Settings(_env_file=env_file)

    assert validate_runtime_settings(settings) is settings
