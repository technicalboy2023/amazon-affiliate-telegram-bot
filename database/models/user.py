"""
User model - Telegram users who interact with the bot.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    affiliate_tags = relationship(
        "AffiliateTag", back_populates="user", cascade="all, delete-orphan"
    )
    telegram_accounts = relationship(
        "TelegramAccount", back_populates="user", cascade="all, delete-orphan"
    )
    source_channels = relationship(
        "SourceChannel", back_populates="user", cascade="all, delete-orphan"
    )
    dest_channels = relationship("DestChannel", back_populates="user", cascade="all, delete-orphan")
    automation_pipelines = relationship(
        "AutomationPipeline", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, tg_id={self.telegram_id}, username={self.username})>"
