"""
Channel models - source channels to monitor and destination channels to post to.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin


class SourceChannel(Base, TimestampMixin):
    __tablename__ = "source_channels"
    __table_args__ = (UniqueConstraint("user_id", "channel_username"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user = relationship("User", back_populates="source_channels")
    telegram_account = relationship("TelegramAccount", back_populates="source_channels")

    def __repr__(self) -> str:
        return f"<SourceChannel(id={self.id}, username={self.channel_username}, active={self.is_active})>"


class DestChannel(Base, TimestampMixin):
    __tablename__ = "dest_channels"
    __table_args__ = (UniqueConstraint("user_id", "channel_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affiliate_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    amazon_domain: Mapped[str] = mapped_column(String(50), default="amazon.in", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="dest_channels")
    automation_pipelines = relationship("AutomationPipeline", back_populates="destination_channel")

    def __repr__(self) -> str:
        return f"<DestChannel(id={self.id}, username={self.channel_username}, tag={self.affiliate_tag})>"
