"""
Automation pipeline model - user-owned monitoring and publishing workflow.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin


class AutomationPipeline(Base, TimestampMixin):
    __tablename__ = "automation_pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("telegram_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    destination_channel_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dest_channels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    affiliate_tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("affiliate_tags.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    skip_duplicates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    duplicate_window_hours: Mapped[int] = mapped_column(Integer, default=720, nullable=False)
    preserve_formatting: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preserve_media: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="automation_pipelines")
    telegram_account = relationship("TelegramAccount", back_populates="automation_pipelines")
    destination_channel = relationship("DestChannel", back_populates="automation_pipelines")
    affiliate_tag = relationship("AffiliateTag")

    def __repr__(self) -> str:
        return f"<AutomationPipeline(id={self.id}, user_id={self.user_id}, status={self.status})>"
