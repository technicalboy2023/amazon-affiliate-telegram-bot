"""
Telegram account model - per-user Telethon account/session ownership.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin


class TelegramAccount(Base, TimestampMixin):
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="telegram_accounts")
    source_channels = relationship("SourceChannel", back_populates="telegram_account")
    automation_pipelines = relationship("AutomationPipeline", back_populates="telegram_account")

    def mark_connected(self) -> None:
        self.status = "connected"
        self.last_connected_at = datetime.now(UTC)
        self.last_error = None

    def __repr__(self) -> str:
        return f"<TelegramAccount(id={self.id}, user_id={self.user_id}, status={self.status})>"
