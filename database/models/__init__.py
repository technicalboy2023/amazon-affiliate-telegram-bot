"""Database models package."""

from database.models.base import Base
from database.models.channel import DestChannel, SourceChannel
from database.models.duplicate import DuplicateCache
from database.models.message import ProcessedMessage
from database.models.pipeline import AutomationPipeline
from database.models.settings import AppSetting
from database.models.stats import DailyStat
from database.models.telegram_account import TelegramAccount
from database.models.user import User

# AffiliateTag model kept for SQLAlchemy relationship resolution in User/AutomationPipeline
from database.models.affiliate import AffiliateTag  # noqa: F401

__all__ = [
    "Base",
    "User",
    "AffiliateTag",
    "SourceChannel",
    "DestChannel",
    "ProcessedMessage",
    "TelegramAccount",
    "AutomationPipeline",
    "DailyStat",
    "DuplicateCache",
    "AppSetting",
]
